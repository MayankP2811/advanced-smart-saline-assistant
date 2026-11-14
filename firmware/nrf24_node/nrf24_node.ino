// Smart Saline bedside node (Arduino Uno): patient vitals + NRF24 radio link.
//
// Reads the patient's heart rate (MAX30102) and body temperature (MLX90614),
// and sends them to the Raspberry Pi with the drip readings every 500 ms.
// It also prints any command bytes received from the Pi.
//
// The drip readings (bottle, rate, drop count) are fixed sample values here:
// the load-cell, IR drop-counting and servo code is not part of this sketch.
//
// Libraries (Arduino Library Manager):
//   RF24                                  by TMRh20
//   Adafruit MLX90614 Library             by Adafruit
//   SparkFun MAX3010x Pulse and Proximity Sensor Library  by SparkFun
//
// Wiring (Uno): nRF24L01 on SPI with CE = 10, CSN = 9.
//               MLX90614 and MAX30102 share I2C: SDA = A4, SCL = A5.

#include <SPI.h>
#include <Wire.h>
#include <RF24.h>
#include <Adafruit_MLX90614.h>
#include "MAX30105.h"   // SparkFun library; also drives the MAX30102
#include "heartRate.h"  // beat detection from the same library

// Six 16-bit values (an int is 2 bytes on the Uno) = 12-byte packet.
// The Raspberry Pi decodes them in this order (see hardware/README.md).
struct NodePacket {
  int sensorNum;    // node ID: 1, 2 or 3
  int bottle;       // bottle reading (sample value in this sketch)
  int rate;         // drop-rate reading (sample value in this sketch)
  int count;        // drop count (sample value in this sketch)
  int heartRate;    // beats per minute, 0 = no finger / no beat yet
  int tempTenths;   // body temperature in tenths of a degree C (368 = 36.8 C), 0 = no reading
};

const int NODE_ID = 1;                       // node 2: set to 2 and change both addresses to ...E2
const uint64_t node_TX = 0xF0F0F0F0E1LL;     // readings to the Pi
const uint64_t node_RX = 0xC0C0F0F0E1LL;     // commands from the Pi

RF24 radio(10, 9);  // CE, CSN
Adafruit_MLX90614 thermometer;
MAX30105 pulseSensor;

NodePacket packet;
bool haveThermometer = false;
bool havePulseSensor = false;

// Heart-rate averaging (from the SparkFun heart-rate example).
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
unsigned long lastBeat = 0;
int beatAvg = 0;

unsigned long lastSend = 0;
unsigned long lastTempRead = 0;

void setup() {
  Serial.begin(9600);

  radio.begin();
  radio.setPALevel(RF24_PA_MAX);
  radio.setDataRate(RF24_250KBPS);
  radio.setChannel(0x77);
  radio.setAutoAck(false);  // matches the Raspberry Pi receiver
  radio.enableDynamicPayloads();
  radio.openWritingPipe(node_TX);
  radio.openReadingPipe(1, node_RX);
  radio.startListening();

  haveThermometer = thermometer.begin();
  if (!haveThermometer) Serial.println("MLX90614 not found: temperature will be sent as 0");

  havePulseSensor = pulseSensor.begin(Wire, I2C_SPEED_FAST);
  if (havePulseSensor) {
    pulseSensor.setup();                    // default settings
    pulseSensor.setPulseAmplitudeRed(0x0A); // low red LED: shows the sensor is on
    pulseSensor.setPulseAmplitudeGreen(0);  // green LED not used
  } else {
    Serial.println("MAX30102 not found: heart rate will be sent as 0");
  }

  packet.sensorNum = NODE_ID;
  packet.bottle = 11;  // sample drip readings
  packet.rate = 12;
  packet.count = 13;
}

// Call as often as possible: beat detection needs a fast, steady stream of samples.
void updateHeartRate() {
  if (!havePulseSensor) return;
  long ir = pulseSensor.getIR();
  if (ir < 50000) {  // no finger on the sensor
    beatAvg = 0;
    return;
  }
  if (checkForBeat(ir)) {
    unsigned long now = millis();
    float bpm = 60.0 / ((now - lastBeat) / 1000.0);
    lastBeat = now;
    if (bpm > 20 && bpm < 255) {
      rates[rateSpot++] = (byte)bpm;
      rateSpot %= RATE_SIZE;
      int sum = 0;
      for (byte i = 0; i < RATE_SIZE; i++) sum += rates[i];
      beatAvg = sum / RATE_SIZE;
    }
  }
}

void updateTemperature() {
  if (!haveThermometer) return;
  if (millis() - lastTempRead < 1000) return;  // once a second is plenty
  lastTempRead = millis();
  double c = thermometer.readObjectTempC();
  packet.tempTenths = isnan(c) ? 0 : (int)(c * 10 + 0.5);
}

void receiveCommands() {
  if (!radio.available()) return;
  byte payload[32] = {0};
  uint8_t size = radio.getDynamicPayloadSize();
  if (size > 32) size = 32;
  radio.read(payload, size);
  Serial.print("Command received:");
  for (uint8_t i = 0; i < size; i++) {
    Serial.print(' ');
    Serial.print(payload[i]);
  }
  Serial.println();
}

void sendReadings() {
  if (millis() - lastSend < 500) return;
  lastSend = millis();
  packet.heartRate = beatAvg;
  radio.stopListening();
  radio.write(&packet, sizeof(packet));
  radio.startListening();
  Serial.print("Sent: HR ");
  Serial.print(packet.heartRate);
  Serial.print(" bpm, temp ");
  Serial.print(packet.tempTenths / 10.0, 1);
  Serial.println(" C");
}

void loop() {
  updateHeartRate();
  updateTemperature();
  receiveCommands();
  sendReadings();
}
