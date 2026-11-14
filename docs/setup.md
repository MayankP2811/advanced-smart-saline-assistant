# Setup

## What you need

- A Raspberry Pi with SPI enabled, and an NRF24L01 module wired as in the [hardware guide](../hardware/README.md).
- A MySQL or MariaDB database, with its own user for this app.
- Python 3.

## Install and run on the Raspberry Pi

From the repository folder:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-hardware.txt

export DATABASE_URL='mysql+pymysql://saline_user:YOUR_PASSWORD@localhost/saline'
export SECRET_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"

.venv/bin/flask --app software/web/app.py init-clinician
.venv/bin/flask --app software/web/app.py run --host 127.0.0.1
```

`init-clinician` creates the database tables, then asks for your email, name, password, and a **security code**. The security code is shared by the ward and is needed to register patients and start therapies. Run it again to add more clinicians (the security code is only set the first time). No patient data is added.

Open http://127.0.0.1:5000 and log in.

Keep the same `SECRET_KEY` between restarts. Otherwise everyone is logged out each time the app restarts. Run a single app process, because the radio can only be used by one process at a time.

The development server only listens on the Pi itself (`127.0.0.1`). To use the dashboard from other computers on the ward network, run it behind a proper web server; that setup isn't included here.

## Settings

Set these as environment variables (`.env` files aren't loaded automatically). See `.env.example`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | required | Database connection |
| `SECRET_KEY` | random on each start | Keeps logins valid across restarts |
| `TELEMETRY_STALE_SECONDS` | `5` | Seconds before a silent bedside node is shown as not connected |
| `HARDWARE_COMMAND_SCRIPT` | `software/web/sender.py` | Use a different command sender |

## Using the schema file instead

`database/schema.sql` creates the same tables by hand:

```bash
mysql saline < database/schema.sql
```

**Upgrading a database from the 2024 version:** phone numbers were stored as whole numbers, which can't hold 10-digit mobile numbers. Run this once:

```bash
mysql saline < database/upgrade-2026.sql
```

## Run the tests

The tests use a temporary SQLite database, a fake radio and a fake command sender, so they run on any computer.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

To run the same tests against an **empty** MySQL/MariaDB database (all of its tables are dropped first):

```bash
TEST_DATABASE_URL='mysql+pymysql://user:password@localhost/saline_test' .venv/bin/python -m pytest tests -q
```

[Back to README](../README.md)
