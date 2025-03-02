# README.md
# Bill Review Validation System

## Overview
This system validates healthcare bills against a reference database, performing multiple validation steps including:
- Line item validation
- Rate validation
- Modifier checks
- Unit validation
- Bundle checks

## Project Structure
```
bill_review/
├── config/
│   └── settings.py         # Configuration and constants
├── core/
│   ├── models/
│   │   ├── validation.py   # Data models
│   │   └── hcfa.py        # HCFA models
│   ├── services/
│   │   ├── database.py     # Database operations
│   │   ├── logger.py       # Logging functionality
│   │   └── normalizer.py   # Data normalization
│   └── validators/
│       ├── line_items.py   # Line item validation
│       ├── modifiers.py    # Modifier validation
│       ├── rates.py        # Rate validation
│       └── units.py        # Units validation
├── utils/
│   └── helpers.py          # Utility functions
├── tests/                  # Test suite
├── requirements.txt        # Project dependencies
├── README.md              # Project documentation
└── main.py                # Entry point

```

## Requirements
- Python 3.7 or higher
- Dependencies listed in requirements.txt
- SQLite database with required schema

## Setup
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure paths in config/settings.py:
   - JSON_PATH: Directory containing HCFA JSON files
   - DB_PATH: Path to SQLite database
   - LOG_PATH: Directory for validation logs

## Usage
Run the validation system:
```bash
python main.py
```

The system will:
1. Process all JSON files in the configured directory
2. Perform validation checks
3. Generate validation logs
4. Save results to the specified log directory

## Input Format
The system supports two JSON formats:

### New Format
```json
{
    "patient_info": {
        "patient_name": "PATIENT NAME"
    },
    "service_lines": [
        {
            "date_of_service": "2024-01-01",
            "cpt_code": "12345",
            "modifiers": ["LT"],
            "units": 1
        }
    ],
    "billing_info": {
        "billing_provider_tin": "123456789"
    },
    "Order_ID": "UUID"
}
```

### Legacy Format
```json
{
    "patient_name": "PATIENT NAME",
    "date_of_service": "2024-01-01",
    "Order_ID": "UUID",
    "line_items": [
        {
            "cpt": "12345",
            "modifier": "LT",
            "units": 1
        }
    ]
}
```

## Validation Steps
1. **Modifier Check**: Validates modifiers against allowed values
2. **Units Check**: Ensures proper unit counts, especially for non-ancillary codes
3. **Line Items**: Compares line items between HCFA and database
4. **Rate Validation**: Verifies rates based on provider network status

## Output
Validation results are saved as JSON files containing:
- Validation status for each check
- Detailed error messages
- Source data references
- Timestamps and file information

## Error Handling
- Each validation step includes detailed error reporting
- Processing continues even if individual files fail
- All errors are logged for review

## Contributing
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with detailed description
4. Ensure all tests pass

## License
[Insert your license information here]