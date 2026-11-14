# Advanced Smart Saline Assistance System

An IoT system that watches IV saline drips **and each patient's heart rate and body temperature** at the bedside, and lets nurses monitor and control a whole ward from one dashboard — over a local radio link, with no internet needed.

**B.E. Electronics & Telecommunication · VCET, University of Mumbai · 2023–2024 · Team project**<br>
Runner-up at VNPS 2024 and Oscillations 2024 · [All awards](#awards)

[![Watch the narrated explainer video](docs/images/video-thumbnail.jpg)](docs/videos/smart-saline-explainer.mp4)

*Click to watch the narrated explainer (1 min 49 s, sound on): the problem, the bedside unit and its vital-sign sensors, the radio link, the live dashboard and the 3D-printed parts.*

## The problem

In most wards, nurses set the drip rate by hand with a roller clamp, and check every bottle and the patient's pulse and temperature in person. A survey of more than ten hospitals and health centres in the Vasai-Virar area, done for this project, pointed to the same gaps: manual rate setting, no alert when a bottle runs low, and no live view of how much fluid is left. Infusion pumps solve this but cost far more.

## What it does

- **Measures the drip at each bed.** An IR sensor in a 3D-printed housing counts drops, and a load cell weighs the bottle.
- **Watches the patient's vital signs.** A MAX30102 sensor on the fingertip measures heart rate, and an MLX90614 infrared thermometer measures body temperature without contact.
- **Controls the flow.** A servo-driven mechanism squeezes the IV tube to set, slow or stop the drip.
- **Works without internet.** Bedside units talk to a central Raspberry Pi over NRF24L01 radio (2.4 GHz).
- **Gives the ward one dashboard.** Clinicians log in, register patients, start a therapy on a channel, watch the drip and vital signs live, and send Start, Stop, Finish and new-rate commands. A fever or an abnormal heart rate is flagged on the patient's card.
- **Does the maths.** It calculates the drop rate from volume, drop factor and infusion time, and estimates the time remaining.

## Architecture

![Ward architecture: four bedside units talk over offline NRF24 radio to a central Raspberry Pi running the Flask app; data goes to MySQL, a Pi touch display and a web portal; staff act on dashboard alerts](docs/images/ward-architecture.svg)

1. Each **bedside unit** (Arduino Uno) reads the drip sensors and the patient's heart rate and temperature, and drives the tube-squeezing servo.
2. It sends readings over **NRF24 radio** to the **Raspberry Pi** at the nurses' station.
3. The Pi runs the **Flask web app** with a **MySQL** database. Staff use it on the Pi's touch display or in a browser, and their commands go back to the bed over the same radio link.

More detail: [how a reading travels](docs/architecture.md) · [radio settings and packet format](hardware/README.md)

## 3D-printed parts

Both parts were designed by the team and 3D-printed for the prototype.

| Drip-chamber housing | Tube-squeezing mechanism |
| --- | --- |
| <img src="docs/images/drip-chamber-housing.gif" width="300" alt="Rotating 3D model of the drip-chamber housing"> | <img src="docs/images/tube-squeezing-mechanism.gif" width="300" alt="Rotating 3D model of the tube-squeezing mechanism"> |
| Clamps around the drip chamber and holds the IR sensor that counts each drop. [Full video](docs/videos/drip-chamber-housing-3d.mp4) | Servo mount that pinches the IV tube to set the flow. [Full video](docs/videos/tube-squeezing-mechanism-3d.mp4) |

## Screenshots

![Ward view: two active patients with live drip readings, heart rate and temperature; one card warns "Check vitals: temperature 38.3 °C"](docs/images/dashboard-ward.png)

*Ward view: every active bed with its drip and vital signs. Rahul's card is flagged for a temperature of 38.3 °C.*

![Patient page: patient details, the active therapy on channel 1 with live bottle, rate, heart rate and body temperature readings, time remaining, and Start, Stop, Finish and Change drop rate controls](docs/images/dashboard-current.png)

*Patient page. Both screenshots are this version running with sample data and a simulated radio.*

<details>
<summary>The prototype in the lab, and the original 2024 dashboard</summary>

| Prototype | Lab setup |
| --- | --- |
| <img src="docs/images/prototype-lab.jpg" width="300" alt="Prototype IV stand with the drip-chamber housing, tube-squeezing unit and controller box"> | <img src="docs/images/lab-setup.jpg" width="460" alt="Lab bench with the prototype IV stand, a second stand, and computers showing the dashboard"> |

![Original 2024 patient page showing device 3 with fluid consumption, time remaining and drop rate](docs/images/dashboard-original.png)

</details>

## Hardware

| Part | Used for |
| --- | --- |
| Arduino Uno | Bedside controller |
| IR sensor module (in the 3D-printed housing) | Counting drops |
| 1 kg load cell with HX711 amplifier | Weighing the bottle |
| MAX30102 pulse sensor (fingertip) | Patient heart rate |
| MLX90614 infrared thermometer | Patient body temperature, without contact |
| MG995 servo (in the tube-squeezing mechanism) | Pressing the IV tube |
| nRF24L01 transceivers | Offline 2.4 GHz radio link |
| Raspberry Pi with a TFT touch display | Central receiver, web server and nurses' display |
| OLED display and buzzer | Bedside readout and alerts |

**Approximate component cost:** ₹1,650 per bedside unit and ₹9,100 for the central station.

See the [block diagram](docs/architecture.md#hardware) for how the parts connect.

## Bench results

The team measured the drop rate at different servo rotations, for a 60-minute infusion:

| Bottle (mL) | Drop factor (drops/mL) | Servo rotation | Measured drops/min (average) |
| --- | --- | --- | --- |
| 1000 | 10 | 30–40° | 82 |
| 1000 | 15 | 20–30° | 65 |
| 1000 | 20 | 10–20° | 46 |
| 500 | 10 | 30–40° | 78 |
| 500 | 15 | 20–30° | 60 |
| 500 | 20 | 10–20° | 42 |

*From the team's prototype tests.*

## What's in this repository

| Included | Not included |
| --- | --- |
| Flask web app, database models and pages | Arduino firmware for the load cell, drop counting and servo |
| Raspberry Pi NRF24 receiver and command sender | Calibration of the drip readings (bottle, rate and count are raw values) |
| Arduino sketch that reads heart rate and body temperature and sends them by radio | Confirmation from the device that a command was carried out |
| MySQL schema, automated tests, docs, paper, images and videos | |

This is an educational prototype. It is **not** a clinically validated medical device. See [implementation status](docs/assessment.md) for what has and hasn't been tested.

## Run it

**On a Raspberry Pi** with the NRF24 radio wired up ([hardware guide](hardware/README.md)) and a MySQL database:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-hardware.txt
export DATABASE_URL='mysql+pymysql://saline_user:YOUR_PASSWORD@localhost/saline'
export SECRET_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
.venv/bin/flask --app software/web/app.py init-clinician   # creates tables and your login
.venv/bin/flask --app software/web/app.py run --host 127.0.0.1
```

Then open http://127.0.0.1:5000 and log in. Full steps: [setup guide](docs/setup.md).

**Run the tests on any computer** (no hardware or MySQL needed):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
```

## Repository layout

| Path | Contents |
| --- | --- |
| `software/web/` | Flask app (`app.py`), radio receiver (`rx.py`, `telemetry.py`), command sender (`commands.py`, `sender.py`), pages and assets |
| `firmware/` | Arduino sketch: heart rate, body temperature and the NRF24 radio link |
| `hardware/` | Radio settings, packet format and command list |
| `database/` | MySQL schema and the upgrade script for 2024 databases |
| `tests/` | Automated tests (fake radio, temporary database) |
| `docs/` | Architecture, setup, status, project history, awards, paper, images and videos |

## Awards

| Event | Result |
| --- | --- |
| VNPS 2024 — VCET national-level project showcase | Runner-up |
| Oscillations 2024 — VCET technical paper presentation | Runner-up |
| Techathon 2024 — TSEC, 48-hour hardware hackathon | Consolation prize |
| Avishkar 2023 (University of Mumbai) and Electrowiz 2024 (DMCE) | Participants |

[Certificates](docs/evidence/achievements.pdf) · [Details](docs/recognition.md)

## Team

**Chandan Thakur · Mayank Patil · Manthan Patil · Omkar Joshi**

Mayank Patil was the project architect and backend developer, and maintains this repository.

Guided by **Dr. Sunayana Jadhav** and **Mr. Sanjay Lohar**. Read the team's [technical paper](docs/research/technical-paper.docx).

---

[Project history](docs/provenance.md) · [Third-party credits and licensing](THIRD_PARTY_NOTICES.md)
