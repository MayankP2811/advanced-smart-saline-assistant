import subprocess
import sys
from types import SimpleNamespace

from commands import dispatch_command


def test_missing_sender_does_not_report_device_success(tmp_path, monkeypatch):
    monkeypatch.setenv('HARDWARE_COMMAND_SCRIPT', str(tmp_path/'missing.py'))
    def unexpected(*args, **kwargs):
        raise AssertionError('No sender should run')
    monkeypatch.setattr(subprocess, 'run', unexpected)
    response, status = dispatch_command(1, 34)
    assert status == 501 and not response['command_dispatched']
    assert dispatch_command(4, 34)[1] == 400
    assert dispatch_command(1, 999)[1] == 400


def test_sender_argument_contract_and_unacknowledged_result(tmp_path, monkeypatch):
    script = tmp_path/'original sender.py'
    script.write_text('# Isolated test fixture; never executed.\n')
    monkeypatch.setenv('HARDWARE_COMMAND_SCRIPT', str(script))
    calls = []
    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(subprocess, 'run', fake_run)
    response, status = dispatch_command(2, 20, 30, 50)
    assert calls[0][0] == [sys.executable, str(script), '2', '20', '30', '50']
    assert not calls[0][1].get('shell', False)
    assert status == 200 and response['command_dispatched']
    assert response['device_acknowledged'] is False
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1))
    assert dispatch_command(1, 34)[1] == 502
    def timeout(*a, **kw):
        raise subprocess.TimeoutExpired(a[0], 5)
    monkeypatch.setattr(subprocess, 'run', timeout)
    assert dispatch_command(1, 55)[1] == 504


def test_default_sender_does_not_claim_third_node_support(monkeypatch):
    monkeypatch.delenv('HARDWARE_COMMAND_SCRIPT', raising=False)
    result, status = dispatch_command(3, 34)
    assert status == 501 and not result['command_dispatched']
    assert 'nodes 1 and 2' in result['message']
