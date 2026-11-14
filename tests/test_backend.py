import importlib
import os
import sys
from datetime import date
from itertools import cycle
from pathlib import Path

import pytest

from fixtures.radio_packets import generate_random_data

CODE = "test-only-code"


@pytest.fixture
def backend(tmp_path, monkeypatch):
    # Set TEST_DATABASE_URL to run these tests against an empty MySQL/MariaDB database instead.
    database_url = os.environ.get("TEST_DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", database_url or "sqlite:///" + str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("HARDWARE_COMMAND_SCRIPT", str(tmp_path / "missing-sender.py"))
    sys.modules.pop("app", None)
    mod = importlib.import_module("app")
    mod.app.config.update(TESTING=True)
    if database_url:
        with mod.app.app_context():
            mod.db.drop_all()
    result = mod.app.test_cli_runner().invoke(args=[
        "init-clinician", "--email", "test@example.invalid", "--name", "Test Clinician",
        "--password", "test-only-password", "--authorization-code", CODE])
    assert result.exit_code == 0, result.output
    with mod.app.app_context():
        for reg_id, name in ((1, "Test"), (2, "Second")):
            mod.db.session.add(mod.patient_reg(
                RegID=reg_id, fname=name, lname="Patient", age=30, dob=date(1994, 1, 1), height=170,
                weight=70, fcno="9876543210", blood="O+", gender="Male", handler="Test Clinician"))
        mod.db.session.flush()
        mod.db.session.add(mod.IVDetails(
            RegID=1, bp=120, sugar=90, pulse=70, iv_type="Test", drop_factor=20, drop_rate=30, size=500,
            status="Active", channel=1, add_info="Synthetic test record"))
        mod.db.session.commit()

    class ReceiverFixture:
        frames = cycle([generate_random_data(node) for node in (1, 2, 3)])
        def read(self): return next(self.frames)

    from telemetry import TelemetryService
    mod.telemetry = TelemetryService(receiver=ReceiverFixture())
    client = mod.app.test_client()
    yield mod, client
    with mod.app.app_context():
        mod.db.session.remove()
        mod.db.engine.dispose()


def csrf(client):
    client.get("/")
    with client.session_transaction() as session:
        return session["csrf_token"]


def login(client, password="test-only-password"):
    """Log in and return the CSRF token of the new session."""
    response = client.post("/", data={"email": "test@example.invalid", "upass": password, "csrf_token": csrf(client)})
    return response, csrf(client)


def therapy_form(token, **changes):
    form = {"RegID": 2, "bp": 120, "sugar": 90, "pulse": 70, "iv_type": "Test", "drop_factor": 20,
            "infuTime": 300, "size": 500, "channel": 2, "addinfo": "Fictional", "security_code": CODE,
            "csrf_token": token}
    form.update(changes)
    return form


def patient_form(token, **changes):
    form = {"fname": "Fictional", "lname": "Example", "age": 25, "dob": "1999-01-01", "height": 170,
            "weight": 70, "fcno": "+91 98765 43210", "phone": "9876543211", "blood": "O+", "gender": "Male",
            "handler": "Test Clinician", "security_code": CODE, "csrf_token": token}
    form.update(changes)
    return form


def flashes(client):
    with client.session_transaction() as session:
        return [message for _, message in session.get("_flashes", [])]


def test_login_and_pages(backend):
    mod, client = backend
    assert client.get("/index").status_code == 302
    response, _ = login(client, "wrong")
    assert response.status_code == 200 and b"Invalid email or password" in response.data
    response, _ = login(client)
    assert response.status_code == 302
    for path in ["/index", "/Inactive", "/reg", "/patient/1", "/patient/2"]:
        assert client.get(path).status_code == 200, path
    assert b"Body temperature" in client.get("/patient/1").data
    index = client.get("/index").data
    assert b"Heart rate" in index and b"Temperature" in index
    assert client.get("/patient/999").status_code == 404
    assert client.get("/patient/abc").status_code == 404
    with mod.app.app_context():
        assert mod.Docs.query.first().password != "test-only-password"
    again = mod.app.test_cli_runner().invoke(args=[
        "init-clinician", "--email", "test@example.invalid", "--name", "Test Clinician",
        "--password", "x", "--authorization-code", "x"])
    assert again.exit_code != 0


def test_dashboard_lists_each_active_patient_once(backend):
    _, client = backend
    login(client)
    html = client.get("/index").get_data(as_text=True)
    assert html.count("Test Patient") == 1 and "Second Patient" not in html
    inactive = client.get("/Inactive").get_data(as_text=True)
    assert "Second Patient" in inactive and "Test Patient" not in inactive


def test_live_readings_and_device_commands(backend):
    _, client = backend
    _, token = login(client)
    for _ in range(20):
        for node in [1, 2, 3]:
            result = client.get(f"/node{node}")
            assert result.status_code == 200
            assert {"z", "a", "b", "c", "d", "e", "f", "online", "source"} <= set(result.json)
            assert result.json["online"] and result.json["a"] == node
            assert 60 <= result.json["e"] <= 100 and 360 <= result.json["f"] <= 375
    for path in ["/buttons", "/reset"]:
        response = client.post(path, json={"ch": 1, "value": 34}, headers={"X-CSRF-Token": token})
        assert response.status_code == 501 and response.json["success"] is False
    response = client.post("/buttons", json={"ch": 1, "value": 99}, headers={"X-CSRF-Token": token})
    assert response.status_code == 400 and "Start" in response.json["message"]


def test_csrf_and_login_required(backend):
    _, client = backend
    assert client.post("/buttons", json={}).status_code == 400
    token = csrf(client)
    assert client.post("/buttons", json={}, headers={"X-CSRF-Token": token}).status_code == 302


def test_register_patient_stores_phone_numbers_as_text(backend):
    mod, client = backend
    _, token = login(client)
    response = client.post("/submit_data", data=patient_form(token))
    assert response.status_code == 302 and "/patient/3" in response.headers["Location"]
    with mod.app.app_context():
        patient = mod.db.session.get(mod.patient_reg, 3)
        assert patient.fcno == "+91 98765 43210" and patient.phone == "9876543211"


@pytest.mark.parametrize("changes,message", [
    ({"security_code": "wrong"}, "Incorrect security code"),
    ({"gender": "none"}, "Select a gender"),
    ({"blood": ""}, "Select a blood group"),
    ({"age": "abc"}, "Age must be a whole number"),
    ({"fcno": "call me"}, "Family contact number must contain"),
    ({"dob": "2999-01-01"}, "cannot be in the future"),
])
def test_register_patient_rejects_bad_input(backend, changes, message):
    mod, client = backend
    _, token = login(client)
    response = client.post("/submit_data", data=patient_form(token, **changes))
    assert response.status_code == 302 and response.headers["Location"].endswith("/reg")
    assert any(message in m for m in flashes(client))
    with mod.app.app_context():
        assert mod.patient_reg.query.count() == 2


def test_new_therapy_is_saved_and_reports_command_result(backend):
    mod, client = backend
    _, token = login(client)
    response = client.post("/submit_iv_details", data=therapy_form(token))
    assert response.status_code == 302 and response.headers["Location"].endswith("/patient/2")
    messages = flashes(client)
    assert "Therapy saved on channel 2 at 33 drops/min." in messages
    assert any("unavailable" in m for m in messages)
    with mod.app.app_context():
        therapy = mod.IVDetails.query.filter_by(RegID=2).one()
        assert therapy.status == "Active" and therapy.drop_rate == 33


@pytest.mark.parametrize("changes,message", [
    ({"security_code": ""}, "Incorrect security code"),
    ({"channel": 1}, "Channel 1 is already in use"),
    ({"RegID": 1, "channel": 3}, "already has an active therapy"),
    ({"infuTime": 0}, "Infusion time (minutes) must be between"),
    ({"size": 1000, "infuTime": 30}, "calculated rate is 666 drops/min"),
    ({"size": 5000}, "Bottle volume (mL) must be between"),
    ({"bp": "120/80"}, "Systolic BP must be a whole number"),
    ({"channel": "none"}, "Channel must be a whole number"),
])
def test_new_therapy_rejects_bad_input_and_double_booking(backend, changes, message):
    mod, client = backend
    _, token = login(client)
    response = client.post("/submit_iv_details", data=therapy_form(token, **changes))
    assert response.status_code == 302
    assert any(message in m for m in flashes(client)), flashes(client)
    with mod.app.app_context():
        assert mod.IVDetails.query.count() == 1


def test_new_therapy_for_unknown_patient_is_404(backend):
    _, client = backend
    _, token = login(client)
    assert client.post("/submit_iv_details", data=therapy_form(token, RegID="abc")).status_code == 404
    assert client.post("/submit_iv_details", data=therapy_form(token, RegID=999)).status_code == 404


def test_finish_works_even_when_the_device_command_fails(backend):
    mod, client = backend
    _, token = login(client)
    response = client.post("/patient/1", data={"status": "Inactive", "csrf_token": token})
    assert response.status_code == 302
    messages = flashes(client)
    assert "Therapy finished." in messages and any(m.startswith("Reset command:") for m in messages)
    with mod.app.app_context():
        assert mod.IVDetails.query.one().status == "Inactive"
    # The channel is free again.
    assert client.post("/check_stat", data={"channel": 1, "csrf_token": token}).json["status"] is False


def test_status_update_only_finishes_known_patients(backend):
    mod, client = backend
    _, token = login(client)
    assert client.post("/patient/1", data={"status": "Banana", "csrf_token": token}).status_code == 400
    assert client.post("/patient/999", data={"status": "Inactive", "csrf_token": token}).status_code == 404
    with mod.app.app_context():
        assert mod.IVDetails.query.one().status == "Active"


def test_change_drop_rate(backend):
    mod, client = backend
    _, token = login(client)
    headers = {"X-CSRF-Token": token}
    response = client.post("/update_drop_rate", json={"RegID": 1, "dropRate": 35, "ch": 1}, headers=headers)
    assert response.status_code == 202 and response.json["record_saved"]
    assert client.post("/update_drop_rate", json={"RegID": 1, "dropRate": 300}, headers=headers).status_code == 400
    assert client.post("/update_drop_rate", json={"RegID": 1, "dropRate": 30, "ch": 2}, headers=headers).status_code == 400
    assert client.post("/update_drop_rate", json={"RegID": 2, "dropRate": 30}, headers=headers).status_code == 404
    with mod.app.app_context():
        assert mod.IVDetails.query.one().drop_rate == 35


def test_security_code_check(backend):
    _, client = backend
    _, token = login(client)
    assert client.post("/check_password", data={"enteredPassword": CODE, "csrf_token": token}).json["success"]
    assert not client.post("/check_password", data={"enteredPassword": "x", "csrf_token": token}).json["success"]


def test_time_remaining_estimate(backend):
    mod, _ = backend
    from datetime import datetime, timedelta, timezone
    therapy = mod.IVDetails(size=500, drop_factor=20, drop_rate=50,
                            timestamp=datetime.now(timezone.utc) - timedelta(minutes=100))
    assert abs(mod.time_remaining(therapy) - 100 * 60) <= 2  # 200 min total, 100 min elapsed


def test_receiver_failure_and_missing_sender(backend, monkeypatch, tmp_path):
    from rx import HardwareUnavailable
    from telemetry import TelemetryService
    mod, client = backend
    _, token = login(client)

    class MissingReceiver:
        def read(self): raise HardwareUnavailable("Radio unavailable")

    mod.telemetry = TelemetryService(receiver=MissingReceiver())
    result = client.get("/node1")
    assert result.status_code == 503 and not result.json["online"] and result.json["a"] == 0
    result = client.post("/buttons", json={"ch": 1, "value": 34}, headers={"X-CSRF-Token": token})
    assert result.status_code == 501 and not result.json["command_dispatched"]
