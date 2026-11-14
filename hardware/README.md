# Radio setup and packet format

## Raspberry Pi radio settings

These settings are in `software/web/rx.py`. The bedside nodes must use the same channel, data rate and addresses.

| Setting | Value |
| --- | --- |
| SPI bus / device | 0 / 0 |
| CE pin | GPIO 17 (BCM numbering) |
| RF channel | `0x77` |
| Data rate | 250 kbps |
| Power | Maximum (`PA_MAX`) |
| Payload | Dynamic length, up to 32 bytes |
| Auto-acknowledge | Off |
| Listening addresses (node 1, 2, 3) | `F0 F0 F0 F0 E1`, `F0 F0 F0 F0 E2`, `F0 F0 F0 F0 E3` |
| Command addresses (node 1, 2) | `C0 C0 F0 F0 E1`, `C0 C0 F0 F0 E2` |

Install the Pi-only packages with `pip install -r requirements-hardware.txt` (`RPi.GPIO`, `spidev`).

## Reading packet (bedside → Pi)

The Arduino sends a struct of six `int` values (12 bytes). On an Arduino Uno each `int` is 2 bytes, little-endian:

| Bytes | Arduino field | Dashboard field | Meaning |
| --- | --- | --- | --- |
| 0–1 | `sensorNum` | `z` / `a` | Node number (1, 2 or 3) |
| 2–3 | `bottle` | `b` | Bottle reading |
| 4–5 | `rate` | `c` | Rate reading |
| 6–7 | `count` | `d` | Drop count |
| 8–9 | `heartRate` | `e` | Heart rate, beats per minute |
| 10–11 | `tempTenths` | `f` | Body temperature in tenths of a °C (368 = 36.8 °C) |

Packets of 10–32 bytes are accepted. A 12-byte (or longer) packet is read as six values; an older 10-byte packet without the temperature is still accepted, and its temperature is reported as `null`. Other boards may use a different `int` size, which would need a change in `rx.py`.

Example: if the sketch sends `1, 11, 12, 13, 76, 368`, then `/node1` returns `b=11, c=12, d=13, e=76` (bpm) and `f=368` (36.8 °C).

## Command packet (Pi → bedside)

`sender.py` sends up to three byte values, padded with zeros to three bytes, every 100 ms for two seconds:

```bash
python software/web/sender.py <channel> <value> [<value> <value>]
```

| Action | Command line |
| --- | --- |
| Start therapy | `sender.py 1 <drop factor> <drop rate> <volume ÷ 10>` |
| Start | `sender.py 1 34` |
| Stop | `sender.py 1 43` |
| Finish / reset | `sender.py 1 55` |
| Change rate | `sender.py 1 <drop rate>` |

The web app runs these for you. The bedside node doesn't reply with a confirmation. Node 3 has no command address in the original design, so commands to it are refused with HTTP 501.

[Setup](../docs/setup.md) · [Arduino example](../firmware/README.md) · [Back to README](../README.md)
