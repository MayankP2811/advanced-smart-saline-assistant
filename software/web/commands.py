"""Run sender.py (or the script in HARDWARE_COMMAND_SCRIPT) to send a device command."""

import os
from pathlib import Path
import subprocess
import sys


def dispatch_command(channel, *values):
    try:
        channel = int(channel)
        values = tuple(int(value) for value in values)
    except (TypeError, ValueError):
        return {"command_dispatched": False, "message": "Invalid command arguments."}, 400
    if channel not in (1, 2, 3) or not values or any(not 0 <= value <= 255 for value in values):
        return {"command_dispatched": False, "message": "Command channel or byte value is out of range."}, 400
    script = Path(os.environ.get("HARDWARE_COMMAND_SCRIPT", str(Path(__file__).with_name("sender.py"))))
    if "HARDWARE_COMMAND_SCRIPT" not in os.environ and channel == 3:
        return {"command_dispatched": False, "message": "The bundled sender supports nodes 1 and 2 only."}, 501
    if not script.is_file():
        return {"command_dispatched": False, "message": "Configured command sender is unavailable."}, 501
    try:
        result = subprocess.run(
            [sys.executable, str(script.resolve()), str(channel), *(str(value) for value in values)],
            cwd=str(script.resolve().parent), capture_output=True, text=True, timeout=5, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"command_dispatched": False, "message": "Command sender timed out; delivery is unknown."}, 504
    except OSError:
        return {"command_dispatched": False, "message": "Command sender could not be started."}, 502
    if result.returncode != 0:
        return {"command_dispatched": False, "message": "Command sender failed; delivery is unknown."}, 502
    return {
        "command_dispatched": True, "device_acknowledged": False,
        "message": "Command sender completed; device execution has not been acknowledged.",
    }, 200
