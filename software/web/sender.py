"""Send a command to bedside node 1 or 2 over the NRF24 radio.

Usage: python sender.py <channel> <value> [<value> <value>]

The command is padded to three bytes and repeated every 100 ms for two seconds.
The node does not send back an acknowledgement.
"""

import argparse
import time

from rx import NRF24Receiver


def send_command(channel, values, receiver=None, clock=time.monotonic, sleep=time.sleep):
    if channel not in (1, 2):
        raise ValueError("The sender supports nodes 1 and 2 only.")
    values = list(values)
    if not 1 <= len(values) <= 3 or any(not 0 <= value <= 255 for value in values):
        raise ValueError("Expected one to three byte-sized command parameters.")
    values.extend([0] * (3 - len(values)))
    receiver = receiver if receiver is not None else NRF24Receiver()
    try:
        receiver.open()
        receiver.radio.stopListening()
        receiver.radio.openWritingPipe([0xC0, 0xC0, 0xF0, 0xF0, 0xE0 + channel])
        payload = values if channel == 1 else bytes(values)
        start = clock()
        while clock() - start < 2:
            receiver.radio.write(payload)
            sleep(0.1)
    finally:
        receiver.close()


def main():
    parser = argparse.ArgumentParser(description="NRF24 command sender for nodes 1 and 2.")
    parser.add_argument("channel", type=int, choices=(1, 2))
    parser.add_argument("values", type=int, nargs="+")
    args = parser.parse_args()
    send_command(args.channel, args.values)


if __name__ == "__main__":
    main()
