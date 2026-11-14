import struct

import pytest

from rx import HardwareUnavailable, NRF24Receiver, decode_payload
from telemetry import TelemetryService


def test_decode_six_field_packet_with_heart_rate_and_temperature():
    frame = [1, 62, 40, 352, 76, 368]  # 76 bpm, 36.8 degrees C
    assert decode_payload(struct.pack('<6h', *frame)) == frame
    assert decode_payload(struct.pack('<6h', *frame) + bytes(20)) == frame


def test_five_field_packet_has_no_temperature():
    assert decode_payload(struct.pack('<5h', 1, 11, 12, 13, 72)) == [1, 11, 12, 13, 72, None]


def test_snapshot_reports_heart_rate_and_temperature():
    service = TelemetryService(FakeReceiver([[3, 62, 40, 352, 76, 368]]))
    data = service.snapshot(3)
    assert data['online'] and data['e'] == 76 and data['f'] == 368
    assert service.snapshot(1)['f'] is None


def test_decode_uno_struct_preserves_full_integer_values():
    frame = [2, 500, 30, 1200, 72]
    assert decode_payload(struct.pack('<5h', *frame)) == frame + [None]
    assert decode_payload(struct.pack('<5h', 1, 11, 12, 13, 14)) == [1, 11, 12, 13, 14, None]
    with pytest.raises(ValueError):
        decode_payload(b'\x01\x00')
    with pytest.raises(ValueError):
        decode_payload(struct.pack('<5h', 4, 1, 2, 3, 4))


class FakeReceiver:
    def __init__(self, frames):
        self.frames = iter(frames)

    def read(self):
        frame = next(self.frames, None)
        if isinstance(frame, Exception):
            raise frame
        return frame


def test_shared_receiver_caches_the_correct_node_and_marks_stale_values():
    clock = [10.0]
    service = TelemetryService(FakeReceiver([[2, 500, 30, 1200, 72]]), clock=lambda: clock[0])
    assert service.snapshot(1)['a'] == 0
    node2 = service.snapshot(2)
    assert node2['a'] == 2 and node2['b'] == 500 and node2['d'] == 1200
    assert node2['source'] == 'nrf24' and node2['online']
    assert not service.snapshot(3)['online']
    clock[0] = 16.0
    stale = service.snapshot(2)
    assert not stale['online'] and stale['a'] == 0
    assert stale['b'] == 500 and stale['age_seconds'] == 6.0


def test_radio_failure_never_substitutes_simulated_readings():
    service = TelemetryService(FakeReceiver([HardwareUnavailable('Radio unavailable')]))
    data = service.snapshot(1)
    assert data['source'] == 'nrf24' and not data['online']
    assert data['a'] == 0 and data['b'] == 0 and data['error'] == 'Radio unavailable'


def test_receiver_read_uses_dynamic_payload_length_without_gpio_imports():
    class Radio:
        def available(self): return True
        def getDynamicPayloadSize(self): return 10
        def read(self, payload, length):
            assert length == 10
            payload.extend(struct.pack('<5h', 3, 500, 30, 1200, 72))
    receiver = NRF24Receiver()
    receiver.radio = Radio()
    assert receiver.read() == [3, 500, 30, 1200, 72, None]
