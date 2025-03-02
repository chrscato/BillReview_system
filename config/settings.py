# config/settings.py
from pathlib import Path

class Settings:
    JSON_PATH = Path(r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Documents\Bill_Review_INTERNAL\scripts\VAILIDATION\data\extracts\valid\mapped\staging")
    DB_PATH = Path(r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Documents\Bill_Review_INTERNAL\reference_tables\orders2.db")
    LOG_PATH = Path(r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Documents\Bill_Review_INTERNAL\validation logs")
    
    # Validation constants
    UNACCEPTABLE_CPTS = {"51655"}
    INVALID_MODIFIERS = {"26", "TC"}

settings = Settings()

# core/models/validation.py
from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class ValidationContext:
    file_name: str
    patient_name: str
    date_of_service: str
    order_id: str

@dataclass
class ValidationResult:
    file_name: str
    timestamp: str
    patient_name: str
    date_of_service: str
    order_id: str
    status: str
    validation_type: str
    details: Dict[str, Any]
    messages: List[str]
    source_data: Dict[str, Any]