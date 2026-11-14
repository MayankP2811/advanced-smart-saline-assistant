import pytest

from telemetry import TelemetryService
from sender import send_command


@pytest.mark.parametrize('channel,values,expected', [(1, [34], [34, 0, 0]), (2, [20, 30, 50], bytes([20, 30, 50]))])
def test_sender_payload_address_and_repeat_interval(channel, values, expected):
    now = [0.0]
    writes = []
    class Radio:
        def stopListening(self): pass
        def openWritingPipe(self, pipe):
            assert pipe == [0xC0, 0xC0, 0xF0, 0xF0, 0xE0 + channel]
        def write(self, payload): writes.append(payload)
    class Receiver:
        radio = Radio()
        closed = False
        def open(self): pass
        def close(self): self.closed = True
    receiver = Receiver()
    def sleep(seconds): now[0] += seconds
    send_command(channel, values, receiver=receiver, clock=lambda: now[0], sleep=sleep)
    assert writes and all(payload == expected for payload in writes)
    assert 19 <= len(writes) <= 21 and now[0] >= 2
    assert receiver.closed


def test_sender_rejects_node_three_without_opening_hardware():
    with pytest.raises(ValueError, match='nodes 1 and 2'):
        send_command(3, [34])


def test_command_serializes_radio_ownership_and_releases_receiver():
    events = []
    class Receiver:
        def close(self): events.append('close')
    service = TelemetryService(Receiver())
    def operation():
        assert service.lock.locked()
        events.append('sender')
        return 'done'
    assert service.command(operation) == 'done'
    assert events == ['close', 'sender', 'close']
    assert not service.lock.locked()
