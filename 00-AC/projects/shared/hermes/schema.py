from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class UserProfile:
    user_id: str
    age: int
    medical_history: list = field(default_factory=list)


@dataclass
class MedicalRecord:
    record_id: str
    user_id: str
    diagnosis: str
    prescription: str
    timestamp: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None
