"""
Property-based tests for storage module.

Uses hypothesis library for property-based testing.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from hypothesis import given, strategies as st, settings

from src.models import AccountRecord
from src.storage import Storage


# Strategy for generating valid email-like strings (no pipe character to avoid parsing issues)
email_strategy = st.emails().filter(lambda x: '|' not in x)

# Strategy for generating password strings (no pipe, newline, or surrogate characters)
password_strategy = st.text(
    alphabet=st.characters(
        blacklist_characters='|\n\r',
        blacklist_categories=('Cs',)  # Exclude surrogate characters
    ),
    min_size=8,
    max_size=50
).filter(lambda x: len(x.strip()) > 0)

# Strategy for generating birthday strings (no pipe character)
birthday_strategy = st.from_regex(r'(January|February|March|April|May|June|July|August|September|October|November|December) [1-9]|[12][0-9]|28', fullmatch=True)


@given(
    email=email_strategy,
    password=password_strategy,
    birthday=birthday_strategy
)
@settings(max_examples=100)
def test_storage_round_trip(email, password, birthday):
    """
    **Feature: ralph-lauren-auto-register, Property 7: 数据存储往返一致性**
    
    *For any* AccountRecord, saving to storage then loading back 
    SHALL produce an equivalent record with identical email, password, and birthday values.
    
    **Validates: Requirements 6.1**
    """
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        temp_path = f.name
    
    try:
        storage = Storage(temp_path)
        
        # Create original record with fixed timestamp for comparison
        original = AccountRecord(
            email=email,
            password=password,
            birthday=birthday,
            created_at=datetime.now()
        )
        
        # Save to storage
        storage.save_success(original)
        
        # Load back from storage
        records = storage.load_all()
        
        # Verify we got exactly one record back
        assert len(records) == 1
        restored = records[0]
        
        # Verify all fields are identical
        assert restored.email == original.email
        assert restored.password == original.password
        assert restored.birthday == original.birthday
        # created_at should be preserved (comparing ISO format strings)
        assert restored.created_at.isoformat() == original.created_at.isoformat()
    finally:
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)


# Strategy for generating a list of account records
account_record_strategy = st.fixed_dictionaries({
    'email': email_strategy,
    'password': password_strategy,
    'birthday': birthday_strategy
})


@given(records_data=st.lists(account_record_strategy, min_size=1, max_size=10))
@settings(max_examples=100)
def test_storage_append_integrity(records_data):
    """
    **Feature: ralph-lauren-auto-register, Property 8: 数据追加保持完整性**
    
    *For any* sequence of save operations, loading all records 
    SHALL return all previously saved records in order without data loss.
    
    **Validates: Requirements 6.2**
    """
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        temp_path = f.name
    
    try:
        storage = Storage(temp_path)
        
        # Create and save multiple records
        original_records = []
        for data in records_data:
            record = AccountRecord(
                email=data['email'],
                password=data['password'],
                birthday=data['birthday'],
                created_at=datetime.now()
            )
            original_records.append(record)
            storage.save_success(record)
        
        # Load all records back
        loaded_records = storage.load_all()
        
        # Verify count matches
        assert len(loaded_records) == len(original_records)
        
        # Verify all records are present in order
        for i, (original, loaded) in enumerate(zip(original_records, loaded_records)):
            assert loaded.email == original.email, f"Email mismatch at index {i}"
            assert loaded.password == original.password, f"Password mismatch at index {i}"
            assert loaded.birthday == original.birthday, f"Birthday mismatch at index {i}"
            assert loaded.created_at.isoformat() == original.created_at.isoformat(), f"Timestamp mismatch at index {i}"
    finally:
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
