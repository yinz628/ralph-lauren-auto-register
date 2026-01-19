"""
Date utilities for Ralph Lauren Auto Register System.

Contains functions for generating random dates within valid ranges.
"""

import random


def generate_random_day() -> int:
    """Generate a random day between 1 and 28 inclusive.
    
    The range 1-28 is used to ensure the day is valid for all months,
    including February in non-leap years.
    
    Returns:
        int: A random day number between 1 and 28 inclusive.
    """
    return random.randint(1, 28)
