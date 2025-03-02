# core/models/hcfa.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class ServiceLine:
    date_of_service: str
    place_of_service: str
    cpt_code: str
    modifiers: List[str]
    diagnosis_pointer: str
    charge_amount: str
    units: int

@dataclass
class PatientInfo:
    patient_name: str
    patient_dob: str
    patient_zip: str

@dataclass
class BillingInfo:
    billing_provider_name: str
    billing_provider_address: str
    billing_provider_tin: str
    billing_provider_npi: str
    total_charge: str
    patient_account_no: str

@dataclass
class HCFAData:
    patient_info: PatientInfo
    service_lines: List[ServiceLine]
    billing_info: BillingInfo
    Order_ID: str
    filemaker_number: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HCFAData':
        """Create HCFAData instance from dictionary"""
        return cls(
            patient_info=PatientInfo(**data['patient_info']),
            service_lines=[ServiceLine(**line) for line in data['service_lines']],
            billing_info=BillingInfo(**data['billing_info']),
            Order_ID=data['Order_ID'],
            filemaker_number=data['filemaker_number']
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert HCFAData instance to dictionary"""
        return {
            'patient_info': {
                'patient_name': self.patient_info.patient_name,
                'patient_dob': self.patient_info.patient_dob,
                'patient_zip': self.patient_info.patient_zip
            },
            'service_lines': [
                {
                    'date_of_service': line.date_of_service,
                    'place_of_service': line.place_of_service,
                    'cpt_code': line.cpt_code,
                    'modifiers': line.modifiers,
                    'diagnosis_pointer': line.diagnosis_pointer,
                    'charge_amount': line.charge_amount,
                    'units': line.units
                }
                for line in self.service_lines
            ],
            'billing_info': {
                'billing_provider_name': self.billing_info.billing_provider_name,
                'billing_provider_address': self.billing_info.billing_provider_address,
                'billing_provider_tin': self.billing_info.billing_provider_tin,
                'billing_provider_npi': self.billing_info.billing_provider_npi,
                'total_charge': self.billing_info.total_charge,
                'patient_account_no': self.billing_info.patient_account_no
            },
            'Order_ID': self.Order_ID,
            'filemaker_number': self.filemaker_number
        }

    def get_line_items(self) -> List[Dict[str, Any]]:
        """Convert service lines to line items format"""
        return [
            {
                'cpt': line.cpt_code,
                'modifier': ','.join(line.modifiers) if line.modifiers else None,
                'units': line.units,
                'charge': line.charge_amount
            }
            for line in self.service_lines
        ]