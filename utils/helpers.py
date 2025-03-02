# utils/helpers.py
def clean_tin(tin):
    """Clean the TIN by removing dashes (-) and whitespace, ensuring 9 digits."""
    if tin is None:
        return None
    cleaned = str(tin).replace("-", "").strip()
    if cleaned.isdigit() and len(cleaned) == 9:
        return cleaned
    return None

def safe_int(value, default=0):
    """Safely convert values to integers"""
    try:
        return int(float(value))  # Handles both string and numeric types
    except (ValueError, TypeError):
        return default