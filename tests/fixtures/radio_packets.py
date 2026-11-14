"""Synthetic packets used only by isolated automated tests."""

import random


def generate_random_data(node):
    """node, bottle, rate, drop count, heart rate (bpm), body temperature (tenths of a degree C)."""
    return [node, random.randint(0, 100), random.randint(1, 60),
            random.randint(0, 255), random.randint(60, 100), random.randint(360, 375)]
