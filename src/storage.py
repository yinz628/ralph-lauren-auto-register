"""
Data storage module for Ralph Lauren Auto Register System.

Handles saving and loading of successful account records.
Uses append mode to preserve existing data.
"""

from pathlib import Path
from typing import List

from src.models import AccountRecord
from src.config import config


class Storage:
    """Storage handler for account records.
    
    Attributes:
        file_path: Path to the storage file
    """
    
    def __init__(self, file_path: str = None):
        """Initialize storage with file path.
        
        Args:
            file_path: Path to storage file. Defaults to config.OUTPUT_FILE
        """
        self.file_path = Path(file_path or config.OUTPUT_FILE)
    
    def save_success(self, record: AccountRecord) -> None:
        """Save a successful account record to storage.
        
        Appends the record to the file without overwriting existing data.
        
        Args:
            record: AccountRecord to save
        """
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(record.to_line() + "\n")
    
    def load_all(self) -> List[AccountRecord]:
        """Load all account records from storage.
        
        Returns:
            List of AccountRecord objects, empty list if file doesn't exist
        """
        if not self.file_path.exists():
            return []
        
        records = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(AccountRecord.from_line(line))
        return records
    
    def clear(self) -> None:
        """Clear all records from storage.
        
        Used primarily for testing purposes.
        """
        if self.file_path.exists():
            self.file_path.unlink()
