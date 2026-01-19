"""
Property-based tests for data models.

Uses hypothesis library for property-based testing.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.models import UserData, AccountRecord


# Strategy for generating valid email-like strings
email_strategy = st.emails()

# Strategy for generating non-empty strings for names
name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L',)),
    min_size=1,
    max_size=50
).filter(lambda x: len(x.strip()) > 0)

# Strategy for generating password strings
password_strategy = st.text(min_size=8, max_size=50).filter(lambda x: len(x.strip()) > 0)

# Strategy for generating phone number strings
phone_strategy = st.from_regex(r'[0-9]{10,15}', fullmatch=True)


@given(
    email=email_strategy,
    first_name=name_strategy,
    last_name=name_strategy,
    password=password_strategy,
    phone_number=phone_strategy
)
@settings(max_examples=100)
def test_user_data_json_round_trip(email, first_name, last_name, password, phone_number):
    """
    **Feature: ralph-lauren-auto-register, Property 1: API数据解析往返一致性**
    
    *For any* valid UserData object, serializing to JSON then parsing back 
    SHALL produce an equivalent UserData object with identical field values.
    
    **Validates: Requirements 1.2**
    """
    # Create original UserData
    original = UserData(
        email=email,
        first_name=first_name,
        last_name=last_name,
        password=password,
        phone_number=phone_number
    )
    
    # Serialize to JSON and parse back
    json_str = original.to_json()
    restored = UserData.from_json(json_str)
    
    # Verify all fields are identical
    assert restored.email == original.email
    assert restored.first_name == original.first_name
    assert restored.last_name == original.last_name
    assert restored.password == original.password
    assert restored.phone_number == original.phone_number
