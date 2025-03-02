# core/models/validation.py
from dataclasses import dataclass
from typing import Dict, List, Any
from datetime import datetime

@dataclass
class ValidationContext:
    file_name: str
    patient_name: str
    date_of_service: str
    order_id: str
from dataclasses import dataclass
from typing import Dict, List, Any
from datetime import datetime

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

    @classmethod
    def create_base_result(cls, file_path: str) -> Dict:
        return {
            "file_name": str(file_path),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "patient_name": None,
            "date_of_service": None,
            "order_id": None,
            "source_data": {}
        }

    def to_dict(self):
        return {
            "file_name": self.file_name,
            "timestamp": self.timestamp,
            "patient_name": self.patient_name,
            "date_of_service": self.date_of_service,
            "order_id": self.order_id,
            "status": self.status,
            "validation_type": self.validation_type,
            "details": self.details,
            "messages": self.messages,
            "source_data": self.source_data
        }
