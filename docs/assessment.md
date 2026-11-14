# Implementation status

## What works and how it was tested

**41 automated tests pass** on Python 3.13 with SQLite, and on MariaDB 10.11 (November 2026). The Arduino sketch compiles for the Arduino Uno. The app was also walked through in a real browser (Chromium) with sample data and a simulated radio: login, registration, starting a therapy, double-booking being blocked, Start/Stop, rate change, Finish and logout. No script errors.

| Area | Covered by tests |
| --- | --- |
| Login | Wrong password rejected, pages need login, passwords stored as hashes, forms protected against cross-site requests (CSRF) |
| Patients | Registration, phone numbers stored as text, bad input rejected with a clear message, security code required |
| Therapies | Drop-rate calculation, 1–255 limit, one active therapy per patient and per channel, Finish works even when the radio command fails |
| Live readings | Packet decoding (with and without temperature), heart rate and temperature in the API, readings stored under the right node, stale readings marked as not connected, radio failure reported |
| Commands | Correct values sent to the sender, failures and time-outs reported, no claim that the device confirmed the command |
| Sender | Radio addresses for nodes 1 and 2, three-byte payload, repeated for two seconds |

## Not tested

- The real NRF24 radio, Raspberry Pi pins, and the Arduino sketch on real sensors (MAX30102, MLX90614). The tests use a fake radio, and the sketch was only compiled.
- The load-cell, drop-counting and servo firmware, which isn't included in this repository.
- Calibration of the drip readings. Bottle, rate and count are raw numbers from the bedside node.
- Reliability with many beds, or over long periods.

## Known limitations

- **Educational prototype.** It isn't clinically validated or certified as a medical device, and its heart-rate and temperature readings aren't a substitute for clinical measurements. Use made-up test data, not real patients.
- **No device confirmation.** The bedside node doesn't confirm that it carried out a command. The dashboard reports only whether the command was sent.
- **Node 3 is read-only.** The bundled sender can send commands to nodes 1 and 2 only.
- **Shared security code.** One code for the whole ward, not per-user permissions.
- **Single process.** The app must run as one process, because it owns the radio.

[Back to README](../README.md)
