# core/services/normalizer.py
from typing import Dict

def normalize_hcfa_format(data: dict) -> dict:
    """
    Convert new HCFA format to the expected format for processing.
    Preserves all necessary information while maintaining compatibility with existing validation logic.
    """
    normalized = {
        'patient_name': data.get('patient_info', {}).get('patient_name'),
        'date_of_service': data.get('service_lines', [{}])[0].get('date_of_service'),
        'Order_ID': data.get('Order_ID'),
        'line_items': [],
        'billing_provider_tin': data.get('billing_info', {}).get('billing_provider_tin'),
        'billing_provider_npi': data.get('billing_info', {}).get('billing_provider_npi'),
        'total_charge': data.get('billing_info', {}).get('total_charge'),
        'raw_data': data
    }
    
    for line in data.get('service_lines', []):
        normalized['line_items'].append({
            'cpt': line.get('cpt_code'),
            'modifier': ','.join(line.get('modifiers', [])) if line.get('modifiers') else None,
            'units': line.get('units', 1),
            'charge': line.get('charge_amount', '0.00')
        })
    
    return normalized