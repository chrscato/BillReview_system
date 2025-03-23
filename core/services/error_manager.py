class ErrorManager:
    # Define error severity levels
    SEVERITY_LEVELS = {
        'CRITICAL': 5,
        'HIGH': 4,
        'MEDIUM': 3,
        'LOW': 2,
        'INFO': 1
    }

    # Define error categories
    CATEGORIES = {
        'billing': 'Billing Error',
        'coding': 'Coding Error',
        'bundle': 'Bundle Error',
        'rate': 'Rate Error',
        'format': 'Format Error'
    }

    # Default configuration for common error codes
    ERROR_CODES = {
        'MOD_001': {'severity': 'MEDIUM', 'category': 'coding', 'resolution': 'Check modifier combinations.'},
        'UNIT_001': {'severity': 'HIGH', 'category': 'coding', 'resolution': 'Verify unit counts.'},
        'RATE_001': {'severity': 'HIGH', 'category': 'rate', 'resolution': 'Ensure rate matches contract.'},
        'BNDL_001': {'severity': 'MEDIUM', 'category': 'bundle', 'resolution': 'Review bundle configuration.'},
        'LINE_001': {'severity': 'MEDIUM', 'category': 'coding', 'resolution': 'Check line item details.'}
    }

    def __init__(self):
        pass

    def get_error_details(self, error_code):
        """Lookup error details from error code."""
        return self.ERROR_CODES.get(error_code, None)

    def calculate_priority(self, severity, financial_impact, network_status):
        """Calculate priority score based on severity, financial impact, and network status."""
        severity_score = self.SEVERITY_LEVELS.get(severity, 0)
        financial_score = financial_impact / 1000  # Example scaling
        network_score = 1 if network_status == 'in-network' else 2
        return severity_score + financial_score + network_score 