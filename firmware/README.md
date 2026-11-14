# Arduino bedside sketch

[`nrf24_node/nrf24_node.ino`](nrf24_node/nrf24_node.ino) runs on the Arduino Uno in each bedside unit. It:

- measures the patient's **heart rate** with a MAX30102 pulse sensor on the fingertip,
- measures **body temperature** with an MLX90614 infrared thermometer (no contact needed),
- sends both to the Raspberry Pi every 500 ms over the NRF24L01 radio, with the drip readings, and
- prints any command it receives from the Pi (Start, Stop, rate changes) to the serial monitor.

The drip readings (bottle, rate, drop count) are sample values in this sketch. The load-cell, IR drop-counting and servo code is not included in this repository.

## Libraries

Install from the Arduino Library Manager:

| Library | For |
| --- | --- |
| RF24 (TMRh20) | NRF24L01 radio |
| Adafruit MLX90614 Library | Body temperature |
| SparkFun MAX3010x Pulse and Proximity Sensor Library | Heart rate (MAX30102) |

For a MAX30100 module instead of a MAX30102, use the MAX30100lib library's `PulseOximeter` in place of the SparkFun code in `updateHeartRate()`.

## Wiring (Arduino Uno)

| Part | Pins |
| --- | --- |
| nRF24L01 | SPI (11, 12, 13), CE = 10, CSN = 9, 3.3 V |
| MLX90614 | I2C: SDA = A4, SCL = A5 |
| MAX30102 | I2C: SDA = A4, SCL = A5 (shares the bus with the MLX90614) |

## Radio settings

| Setting | Value |
| --- | --- |
| RF channel | `0x77` |
| Data rate | 250 kbps |
| Auto-acknowledge | Off (matches the Raspberry Pi) |
| Sends to | `0xF0F0F0F0E1` (node 1) |
| Listens on | `0xC0C0F0F0E1` (node 1 commands) |

**For a second node,** set `NODE_ID` to `2` and change both address endings from `E1` to `E2`.

## What is sent

Six 16-bit values: node ID, bottle, rate, drop count, heart rate (bpm, 0 = no finger or no beat yet), and temperature in tenths of a °C (368 = 36.8 °C, 0 = sensor not found). See the [packet format](../hardware/README.md#reading-packet-bedside--pi).

The sketch compiles for the Arduino Uno (35% of program memory, 39% of RAM). It hasn't been tested on hardware in this repository version.

[Back to README](../README.md)
