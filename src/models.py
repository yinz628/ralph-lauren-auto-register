"""
Data models for Ralph Lauren Auto Register System.

Contains dataclasses for user data, proxy validation results, and account records.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional
import json


@dataclass
class UserData:
    """User data fetched from the API.
    
    Attributes:
        email: User email address
        first_name: User's first name
        last_name: User's last name
        password: User's password
        phone_number: User's phone number
    """
    email: str
    first_name: str
    last_name: str
    password: str
    phone_number: str
    
    def to_json(self) -> str:
        """Serialize UserData to JSON string."""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> "UserData":
        """Deserialize UserData from JSON string."""
        data = json.loads(json_str)
        return cls(**data)
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserData":
        """Create UserData from dictionary."""
        return cls(
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            password=data["password"],
            phone_number=data["phone_number"]
        )


@dataclass
class ProxyValidationResult:
    """Result of proxy validation.
    
    Attributes:
        is_valid: Whether the proxy is valid and usable
        latency_ms: Connection latency in milliseconds
        country: Country code (e.g., "US")
        region: Region/state name
    """
    is_valid: bool
    latency_ms: float
    country: str
    region: str


@dataclass
class AccountRecord:
    """Record of a successfully registered account.
    
    Attributes:
        email: Account email address
        password: Account password
        birthday: Birthday string (e.g., "January 15")
        created_at: Timestamp when the account was created
    """
    email: str
    password: str
    birthday: str
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_json(self) -> str:
        """Serialize AccountRecord to JSON string."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "AccountRecord":
        """Deserialize AccountRecord from JSON string."""
        data = json.loads(json_str)
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
    
    def to_line(self) -> str:
        """Convert to a single line for file storage."""
        return f"{self.email}|{self.password}|{self.birthday}|{self.created_at.isoformat()}"
    
    @classmethod
    def from_line(cls, line: str) -> "AccountRecord":
        """Parse AccountRecord from a storage line."""
        parts = line.strip().split("|")
        return cls(
            email=parts[0],
            password=parts[1],
            birthday=parts[2],
            created_at=datetime.fromisoformat(parts[3])
        )
