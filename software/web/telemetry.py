"""Shared NRF24 radio polling and per-node freshness."""

import threading
import time

from rx import HardwareUnavailable, NRF24Receiver


class TelemetryService:
    def __init__(self, receiver=None, stale_after=5.0, clock=time.monotonic):
        if stale_after <= 0:
            raise ValueError("TELEMETRY_STALE_SECONDS must be positive.")
        self.receiver = receiver if receiver is not None else NRF24Receiver()
        self.stale_after = stale_after
        self.clock = clock
        self.lock = threading.Lock()
        self.nodes = {}

    def command(self, operation):
        """Release the receive handle while the separate sender owns the radio."""
        with self.lock:
            close = getattr(self.receiver, "close", lambda: None)
            close()
            try:
                return operation()
            finally:
                close()

    def snapshot(self, node):
        if node not in (1, 2, 3):
            raise ValueError("Unknown node ID.")
        with self.lock:
            error = None
            try:
                frame = self.receiver.read()
                if frame is not None:
                    self.nodes[frame[0]] = (frame, self.clock())
            except HardwareUnavailable as exc:
                error = str(exc)
            values, received = self.nodes.get(node, ([node, 0, 0, 0, 0, None], None))
            age = None if received is None else max(0, self.clock() - received)
            online = error is None and age is not None and age <= self.stale_after
            return {
                "z": node,
                "a": node if online else 0,
                "b": values[1], "c": values[2], "d": values[3],
                "e": values[4],  # heart rate, beats per minute (0 = no beat detected yet)
                "f": values[5] if len(values) > 5 else None,  # body temperature, tenths of a degree C
                "online": online,
                "age_seconds": None if age is None else round(age, 3),
                "source": "nrf24",
                "error": error,
            }
