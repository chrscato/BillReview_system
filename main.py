import importlib
import core.validators.line_items as line_items
importlib.reload(line_items)
import json
from pathlib import Path
from datetime import datetime
from typing import Dict
import pandas as pd
from config.settings import settings
from core.services.database import DatabaseService
from core.services.logger import JSONValidationLogger
from core.services.normalizer import normalize_hcfa_format
from core.validators.line_items import LineItemValidator
from core.validators.rates import RateValidator
from core.validators.modifiers import ModifierValidator
from core.validators.units import UnitsValidator
from core.models.validation import ValidationResult

class BillReviewApplication:
    def __init__(self):
        self.db_service = DatabaseService()
        self.logger = JSONValidationLogger(Path(settings.LOG_PATH))

    def process_file(self, file_path: Path, validators: Dict) -> None:
        """Process a single JSON file through all validators."""
        base_result = {
            "file_name": str(file_path),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "patient_name": None,
            "date_of_service": None,
            "order_id": None,
            "source_data": {}
        }

        try:
            with open(file_path, 'r') as f:
                raw_hcfa_data = json.load(f)
            
            hcfa_data = normalize_hcfa_format(raw_hcfa_data)
            order_id = hcfa_data.get('Order_ID')

            # Load provider & patient details
            provider_info = self.db_service.get_provider_details(order_id, validators['conn'])
            patient_info = self.db_service.get_full_details(order_id, validators['conn'])['order_details']

            base_result.update({
                "patient_name": hcfa_data.get('patient_name'),
                "date_of_service": hcfa_data.get('date_of_service'),
                "order_id": order_id,
                "source_data": {"hcfa": hcfa_data, "db_provider_info": provider_info, "db_patient_info": patient_info}
            })

            # Modifier validation
            modifier_result = validators['modifier'].validate(hcfa_data)
            if modifier_result['status'] == "FAIL":
                self.logger.log_validation(ValidationResult(**base_result, status="FAIL", validation_type="modifier_check", details=modifier_result, messages=[]))
                return

            # Units validation
            units_result = validators['units'].validate(hcfa_data)
            if units_result['status'] == "FAIL":
                self.logger.log_validation(ValidationResult(**base_result, status="FAIL", validation_type="unit_check", details=units_result, messages=[]))
                return

            # Bundle check - If order is already marked as bundled, skip further validation
            if self.db_service.check_bundle(order_id, validators['conn']):
                self.logger.log_validation(ValidationResult(**base_result, status="FAIL", validation_type="bundle_check", details={}, messages=[]))
                return

            # Line items validation
            order_lines = self.db_service.get_line_items(order_id, validators['conn'])
            line_items_result = validators['line_items'].validate(hcfa_data['line_items'], order_lines)

            # ✅ If line items validation fails, log and exit
            if line_items_result['status'] == "FAIL":
                print("Line item validation failed, skipping rate validation")
                self.logger.log_validation(ValidationResult(
                    **base_result,
                    status="FAIL",
                    validation_type="line_items",
                    details=line_items_result,
                    messages=["Line item validation failed"]
                ))
                return

            # ✅ If it's a bundled claim, proceed with rate validation before marking as PASS
            if line_items_result['status'] == "BUNDLED":
                print(f"Processing bundled claim: {line_items_result['bundle_type']}")

            # ✅ Perform Rate Validation (even for bundled claims)
            rate_result = validators['rate'].validate(hcfa_data['line_items'], order_id)

            if rate_result['status'] == "FAIL":
                print("Rate validation failed")
                self.logger.log_validation(ValidationResult(
                    **base_result,
                    status="FAIL",
                    validation_type="rate",
                    details=rate_result,
                    messages=["Rate validation failed"]
                ))
                return  # 🚨 Prevents failed rates from making it into `validation_passes.json`

            # ✅ If both validations pass, log as PASS
            print("Both validations passed")
            enriched_data = {
                **base_result,
                "status": "PASS",
                "validation_type": "final",
                "details": {**line_items_result, **rate_result},
                "messages": ["Line item and rate validation passed"]
            }
            self.logger.log_validation(ValidationResult(**enriched_data))

        except Exception as e:
            self.logger.log_validation(ValidationResult(
                **base_result,
                status="FAIL",
                validation_type="process_error",
                details={"error": str(e)},
                messages=[f"Error processing file: {str(e)}"]
            ))


    def run(self):
        """Main execution method."""
        with self.db_service.connect_db() as conn:
            dim_proc_df = pd.read_sql_query("SELECT * FROM dim_proc", conn)
            validators = {
                'conn': conn,
                'line_items': LineItemValidator(dim_proc_df),
                'rate': RateValidator(conn),
                'modifier': ModifierValidator(),
                'units': UnitsValidator(dim_proc_df)
            }

            json_files = list(Path(settings.JSON_PATH).glob('*.json'))
            total_files = len(json_files)
            print(f"Found {total_files} files to process")

            for index, json_file in enumerate(json_files, 1):
                print(f"Processing file {index}/{total_files}: {json_file.name}")
                self.process_file(json_file, validators)

        # Save results
        log_file = self.logger.save()
        print(f"Validation complete. Results saved to: {log_file}")

if __name__ == "__main__":
    app = BillReviewApplication()
    app.run()
