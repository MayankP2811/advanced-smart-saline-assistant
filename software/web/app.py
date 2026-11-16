"""Flask web app for the Advanced Smart Saline Assistance System."""

import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from functools import wraps

import click
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

from commands import dispatch_command
from telemetry import TelemetryService

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError('Set DATABASE_URL before starting the application or initializing an account.')

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SQLALCHEMY_DATABASE_URI=DATABASE_URL,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy(app)
telemetry = TelemetryService(stale_after=float(os.environ.get('TELEMETRY_STALE_SECONDS', '5')))

CHANNELS = (1, 2, 3)
BLOOD_GROUPS = ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')
GENDERS = ('Female', 'Male')
PHONE_PATTERN = re.compile(r'^\+?[0-9 -]{7,20}$')


# ---------------------------------------------------------------- models

class patient_reg(db.Model):
    """A registered patient."""
    RegID = db.Column(db.Integer, primary_key=True)
    fname = db.Column('Fname', db.String(80), nullable=False)
    lname = db.Column('Lname', db.String(80), nullable=False)
    age = db.Column('Age', db.Integer, nullable=False)
    dob = db.Column('Dob', db.Date, nullable=False)
    height = db.Column('Height', db.Integer, nullable=False)
    weight = db.Column('Weight', db.Integer, nullable=False)
    fcno = db.Column('FCNo', db.String(20), nullable=False)
    phone = db.Column('PatientPhone', db.String(20))
    blood = db.Column('Blood', db.String(10), nullable=False)
    gender = db.Column('Gender', db.String(10), nullable=False)
    handler = db.Column('Handler', db.String(80), nullable=False)
    Regtime = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class auth(db.Model):
    """The shared security code used to confirm patient and therapy changes."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=False)


class Docs(db.Model):
    """A clinician login."""
    userid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


class IVDetails(db.Model):
    """One IV therapy for a patient, assigned to one bedside channel."""
    __tablename__ = 'iv_details'
    therapy_id = db.Column(db.Integer, primary_key=True)
    RegID = db.Column(db.Integer, db.ForeignKey('patient_reg.RegID'), nullable=False)
    bp = db.Column(db.Integer, nullable=False)
    sugar = db.Column(db.Integer, nullable=False)
    pulse = db.Column(db.Integer, nullable=False)
    iv_type = db.Column(db.String(255), nullable=False)
    drop_factor = db.Column(db.Integer, nullable=False)
    drop_rate = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(255), default='Inactive')
    channel = db.Column(db.Integer, nullable=False)
    add_info = db.Column(db.String(255), nullable=False, default='')


def active_therapy(**filters):
    return IVDetails.query.filter_by(status='Active', **filters).order_by(IVDetails.therapy_id.desc()).first()


# ---------------------------------------------------------------- request helpers

class InvalidInput(ValueError):
    """A form or JSON value the user needs to correct."""


def form_int(name, label, low, high):
    try:
        value = int(request.form.get(name, ''))
    except ValueError:
        raise InvalidInput(f'{label} must be a whole number.')
    if not low <= value <= high:
        raise InvalidInput(f'{label} must be between {low} and {high}.')
    return value


def form_text(name, label, max_length, required=True):
    value = request.form.get(name, '').strip()
    if required and not value:
        raise InvalidInput(f'{label} is required.')
    if len(value) > max_length:
        raise InvalidInput(f'{label} must be at most {max_length} characters.')
    return value


def form_choice(name, label, choices):
    value = request.form.get(name, '')
    if value not in choices:
        raise InvalidInput(f'Select a {label.lower()}.')
    return value


def form_phone(name, label):
    value = form_text(name, label, 20)
    if not PHONE_PATTERN.match(value):
        raise InvalidInput(f'{label} must contain 7 to 20 digits (spaces, "-" and a leading "+" are allowed).')
    return value


def security_code_ok(code):
    record = db.session.get(auth, 1)
    return bool(record and code and check_password_hash(record.password, code))


def require_security_code():
    if not security_code_ok(request.form.get('security_code', '')):
        raise InvalidInput('Incorrect security code.')


def json_error(message, status=400):
    return jsonify(success=False, message=message), status


def command_message(command):
    return command.get('message', 'Device command status unknown.')


# ---------------------------------------------------------------- security

@app.context_processor
def csrf_context():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return {'csrf_token': session['csrf_token']}


@app.before_request
def protect_forms():
    if request.method == 'POST':
        expected = session.get('csrf_token')
        supplied = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            abort(400, description='Missing or invalid CSRF token.')


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))
    return wrap


# ---------------------------------------------------------------- login

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Docs.query.filter_by(email=request.form.get('email', '')).first()
        if user and check_password_hash(user.password, request.form.get('upass', '')):
            session.clear()  # start a fresh session after login
            session['logged_in'] = True
            session['username'] = user.name
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out.', 'success')
    return redirect(url_for('login'))


# ---------------------------------------------------------------- pages

@app.route('/index')
@is_logged_in
def index():
    rows = (db.session.query(patient_reg, IVDetails)
            .join(IVDetails, IVDetails.RegID == patient_reg.RegID)
            .filter(IVDetails.status == 'Active')
            .order_by(IVDetails.timestamp.desc())
            .all())
    return render_template('index.html', rows=rows)


@app.route('/Inactive')
@is_logged_in
def Inactive():
    has_active = db.session.query(IVDetails.therapy_id).filter(
        IVDetails.RegID == patient_reg.RegID, IVDetails.status == 'Active').exists()
    patients = patient_reg.query.filter(~has_active).order_by(patient_reg.Regtime.desc()).all()
    return render_template('Inactive.html', patients=patients)


@app.route('/reg')
@is_logged_in
def reg():
    return render_template('reg.html', blood_groups=BLOOD_GROUPS, genders=GENDERS)


def time_remaining(therapy):
    """Estimate seconds left from the prescribed rate (not from sensor readings)."""
    started = therapy.timestamp
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    total = timedelta(minutes=therapy.size * therapy.drop_factor / therapy.drop_rate)
    return max(0, int((started + total - datetime.now(timezone.utc)).total_seconds()))


@app.route('/patient/<int:id>')
@is_logged_in
def show_patient(id):
    patient = db.session.get(patient_reg, id)
    if patient is None:
        return render_template('page404.html'), 404
    history = IVDetails.query.filter_by(RegID=id).order_by(IVDetails.therapy_id.desc()).all()
    current = next((t for t in history if t.status == 'Active'), None)
    return render_template('patientpage.html', patient=patient, current=current,
                           past=[t for t in history if t.status != 'Active'],
                           remaining=time_remaining(current) if current else None)


# ---------------------------------------------------------------- live readings

def node_response(node):
    data = telemetry.snapshot(node)
    return jsonify(data), 503 if data['error'] else 200


@app.route('/node1')
@is_logged_in
def node1():
    return node_response(1)


@app.route('/node2')
@is_logged_in
def node2():
    return node_response(2)


@app.route('/node3')
@is_logged_in
def node3():
    return node_response(3)


# ---------------------------------------------------------------- patient and therapy changes

@app.route('/submit_data', methods=['POST'])
@is_logged_in
def submit_data():
    try:
        require_security_code()
        dob_text = request.form.get('dob', '')
        try:
            dob = datetime.strptime(dob_text, '%Y-%m-%d').date()
        except ValueError:
            raise InvalidInput('Enter a valid date of birth.')
        if dob > date.today():
            raise InvalidInput('Date of birth cannot be in the future.')
        patient = patient_reg(
            fname=form_text('fname', 'First name', 80),
            lname=form_text('lname', 'Last name', 80),
            age=form_int('age', 'Age', 0, 130),
            dob=dob,
            height=form_int('height', 'Height', 1, 300),
            weight=form_int('weight', 'Weight', 1, 500),
            fcno=form_phone('fcno', 'Family contact number'),
            phone=form_phone('phone', 'Patient contact number'),
            blood=form_choice('blood', 'Blood group', BLOOD_GROUPS),
            gender=form_choice('gender', 'Gender', GENDERS),
            handler=form_text('handler', 'Handling doctor', 80),
        )
    except InvalidInput as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('reg'))
    db.session.add(patient)
    db.session.commit()
    flash(f'Patient {patient.fname} {patient.lname} registered.', 'success')
    return redirect(url_for('show_patient', id=patient.RegID))


@app.route('/submit_iv_details', methods=['POST'])
@is_logged_in
def submit_iv_details():
    reg_id = request.form.get('RegID', '')
    patient = db.session.get(patient_reg, int(reg_id)) if reg_id.isdigit() else None
    if patient is None:
        abort(404)
    back = redirect(url_for('show_patient', id=patient.RegID))
    try:
        require_security_code()
        channel = form_int('channel', 'Channel', 1, 3)
        size = form_int('size', 'Bottle volume (mL)', 1, 2550)
        drop_factor = form_int('drop_factor', 'Drop factor', 1, 255)
        infusion_minutes = form_int('infuTime', 'Infusion time (minutes)', 1, 10000)
        drop_rate = (size * drop_factor) // infusion_minutes
        if not 1 <= drop_rate <= 255:
            raise InvalidInput(f'The calculated rate is {drop_rate} drops/min. The device accepts 1 to 255; '
                               'change the volume or infusion time.')
        if active_therapy(RegID=patient.RegID):
            raise InvalidInput('This patient already has an active therapy. Finish it first.')
        if active_therapy(channel=channel):
            raise InvalidInput(f'Channel {channel} is already in use.')
        therapy = IVDetails(
            RegID=patient.RegID,
            bp=form_int('bp', 'Systolic BP', 40, 300),
            sugar=form_int('sugar', 'Blood sugar', 10, 1000),
            pulse=form_int('pulse', 'Pulse', 20, 250),
            iv_type=form_text('iv_type', 'IV type', 255),
            drop_factor=drop_factor, drop_rate=drop_rate, size=size,
            status='Active', channel=channel,
            add_info=form_text('addinfo', 'Additional instructions', 255, required=False),
        )
    except InvalidInput as exc:
        flash(str(exc), 'danger')
        return back
    db.session.add(therapy)
    db.session.commit()
    command, status = perform_command(channel, drop_factor, drop_rate, size // 10)
    flash(f'Therapy saved on channel {channel} at {drop_rate} drops/min.', 'success')
    flash(command_message(command), 'success' if status == 200 else 'warning')
    return back


@app.route('/patient/<int:id>', methods=['POST'])
@is_logged_in
def update_ch(id):
    """Finish the patient's active therapy, then tell the device to reset."""
    if db.session.get(patient_reg, id) is None:
        abort(404)
    if request.form.get('status') != 'Inactive':
        abort(400, description='Only finishing a therapy is supported.')
    therapy = active_therapy(RegID=id)
    if therapy is None:
        flash('This patient has no active therapy.', 'warning')
        return redirect(url_for('show_patient', id=id))
    therapy.status = 'Inactive'
    db.session.commit()
    flash('Therapy finished.', 'success')
    command, status = perform_command(therapy.channel, 55)
    flash('Reset command: ' + command_message(command), 'success' if status == 200 else 'warning')
    return redirect(url_for('show_patient', id=id))


@app.route('/check_password', methods=['POST'])
@is_logged_in
def check_password():
    return jsonify(success=security_code_ok(request.form.get('enteredPassword', '')))


@app.route('/check_stat', methods=['POST'])
@is_logged_in
def check_stat():
    """Report whether a channel is already in use (shown before the form is sent)."""
    try:
        channel = int(request.form.get('channel', ''))
    except ValueError:
        return json_error('Select a channel.')
    return jsonify(status=active_therapy(channel=channel) is not None)


# ---------------------------------------------------------------- device commands

def perform_command(channel, *values):
    return telemetry.command(lambda: dispatch_command(channel, *values))


def command_response(channel, *values):
    result, status = perform_command(channel, *values)
    return jsonify(success=status == 200, **result), status


@app.route('/buttons', methods=['POST'])
@is_logged_in
def buttons():
    data = request.get_json(silent=True) or {}
    if data.get('value') not in (34, 43, '34', '43'):
        return json_error('A Start (34) or Stop (43) command is required.')
    return command_response(data.get('ch'), int(data['value']))


@app.route('/reset', methods=['POST'])
@is_logged_in
def reset():
    data = request.get_json(silent=True) or {}
    return command_response(data.get('ch'), 55)


@app.route('/update_drop_rate', methods=['POST'])
@is_logged_in
def update_drop_rate():
    data = request.get_json(silent=True) or {}
    try:
        drop_rate = int(data.get('dropRate'))
        reg_id = int(data.get('RegID'))
    except (TypeError, ValueError):
        return json_error('A valid patient and a whole-number rate are required.')
    if not 1 <= drop_rate <= 255:
        return json_error('The rate must be between 1 and 255 drops/min.')
    therapy = active_therapy(RegID=reg_id)
    if therapy is None:
        return json_error('This patient has no active therapy.', 404)
    if data.get('ch') is not None and str(data['ch']) != str(therapy.channel):
        return json_error('Channel does not match the therapy record.')
    therapy.drop_rate = drop_rate
    db.session.commit()
    command, status = perform_command(therapy.channel, drop_rate)
    return jsonify(record_saved=True, command=command), (200 if status == 200 else 202)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('page404.html'), 404


# ---------------------------------------------------------------- setup command

@app.cli.command('init-clinician')
@click.option('--email', prompt=True)
@click.option('--name', prompt=True)
@click.password_option()
@click.option('--authorization-code', prompt=True, hide_input=True, confirmation_prompt=True)
def init_clinician(email, name, password, authorization_code):
    """Create the tables and a clinician login. No patient data is added."""
    db.create_all()
    if Docs.query.filter_by(email=email).first():
        raise click.ClickException('An account with this email already exists.')
    db.session.add(Docs(name=name, email=email, password=generate_password_hash(password)))
    if db.session.get(auth, 1) is None:
        db.session.add(auth(id=1, name='Security code', password=generate_password_hash(authorization_code)))
    db.session.commit()
    click.echo('Clinician account created.')


if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=False)
