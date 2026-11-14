"""Raspberry Pi NRF24L01 receive adapter for the project's radio configuration."""

import struct
import time


class HardwareUnavailable(RuntimeError):
    """The Raspberry Pi radio could not be initialized or read."""


def decode_payload(payload):
    """Decode the UNO/AVR node struct of little-endian signed 16-bit fields.

    Fields: node ID, bottle reading, rate reading, drop count, heart rate (bpm)
    and body temperature (tenths of a degree Celsius). Older five-field packets
    without a temperature are still accepted; their temperature is None.
    """
    if not 10 <= len(payload) <= 32:
        raise ValueError("Expected a 10–32 byte NRF24 payload.")
    count = 6 if len(payload) >= 12 else 5
    values = list(struct.unpack(f"<{count}h", bytes(payload[:count * 2])))
    if count == 5:
        values.append(None)
    if values[0] not in (1, 2, 3):
        raise ValueError("Unknown bedside node ID.")
    return values


class NRF24Receiver:
    """Initialize GPIO/SPI lazily, so importing the web app never touches hardware."""

    def __init__(self):
        self.radio = None
        self.gpio = None
        self.spi = None

    def open(self):
        if self.radio is not None:
            return
        try:
            import RPi.GPIO as GPIO
            import spidev
            from lib_nrf24 import NRF24

            self.gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            self.spi = spidev.SpiDev()
            radio = NRF24(GPIO, self.spi)
            radio.begin(0, 17)
            radio.setPayloadSize(32)
            radio.setChannel(0x77)
            radio.setDataRate(NRF24.BR_250KBPS)
            radio.setPALevel(NRF24.PA_MAX)
            radio.setAutoAck(False)
            radio.enableDynamicPayloads()
            radio.enableAckPayload()
            for pipe, suffix in ((1, 0xE1), (3, 0xE2), (5, 0xE3)):
                radio.openReadingPipe(pipe, [0xF0, 0xF0, 0xF0, 0xF0, suffix])
            radio.startListening()
            self.radio = radio
        except Exception as exc:
            self.close()
            raise HardwareUnavailable("NRF24 receiver unavailable; check GPIO, SPI, and radio wiring.") from exc

    def read(self, timeout=0.05):
        self.open()
        try:
            deadline = time.monotonic() + timeout
            while not self.radio.available():
                if time.monotonic() >= deadline:
                    return None
                time.sleep(0.005)
            size = self.radio.getDynamicPayloadSize()
            if not 10 <= size <= 32:
                self.radio.flush_rx()
                return None
            payload = []
            self.radio.read(payload, size)
            return decode_payload(payload)
        except ValueError:
            return None
        except Exception as exc:
            self.close()
            raise HardwareUnavailable("NRF24 receive operation failed.") from exc

    def close(self):
        self.radio = None
        if self.spi is not None:
            try:
                self.spi.close()
            except Exception:
                pass
            self.spi = None
        if self.gpio is not None:
            try:
                self.gpio.cleanup(17)
            except Exception:
                pass
            self.gpio = None
