"""
Property-based tests for date utilities.

Uses hypothesis library for property-based testing.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.date_utils import generate_random_day


@settings(max_examples=100)
@given(st.random_module())
def test_random_day_range_validity(random_module):
    """
    **Feature: ralph-lauren-auto-register, Property 2: 随机日期范围有效性**
    
    *For any* generated random day, the value SHALL be within the range 
    1 to 28 inclusive.
    
    **Validates: Requirements 1.3**
    """
    # Generate a random day
    day = generate_random_day()
    
    # Verify the day is within valid range
    assert 1 <= day <= 28, f"Generated day {day} is outside valid range [1, 28]"
