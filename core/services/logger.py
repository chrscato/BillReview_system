import json
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any
from core.models.validation import ValidationResult
import uuid

class ValidationErrorCode:
    MODIFIER_INVALID = "MOD_001"
    UNITS_INVALID = "UNIT_001"
    RATE_MISMATCH = "RATE_001"
    BUNDLE_ERROR = "BNDL_001"
    LINE_ITEM_MISMATCH = "LINE_001"
    
    @staticmethod
    def get_description(code: str) -> str:
        descriptions = {
            "MOD_001": "Invalid modifier combination or usage",
            "UNIT_001": "Invalid unit count for procedure",
            "RATE_001": "Rate does not match expected value",
            "BNDL_001": "Invalid bundle configuration",
            "LINE_001": "Line item mismatch with reference data"
        }
        return descriptions.get(code, "Unknown error")

class JSONValidationLogger:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = str(uuid.uuid4())
        self.results: List[ValidationResult] = []

    def _create_failure_record(self, result: ValidationResult) -> Dict[str, Any]:
        """Create a simplified failure record with all data needed for correction interfaces."""
        # Determine the error code based on validation type
        error_code = self._determine_error_code(result)
        
        # Safely get source data
        source_data = result.source_data or {}
        
        # Safely get provider_info with fallback to empty dict
        provider_info = source_data.get("db_provider_info") or {}
        
        # Basic file and validation info
        failure_record = {
            "file_name": result.file_name,
            "order_id": result.order_id,
            "patient_name": result.patient_name,
            "date_of_service": result.date_of_service,
            "validation_type": result.validation_type,
            "error_code": error_code,
            "error_description": ValidationErrorCode.get_description(error_code),
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "status": "FAIL",
            "message": result.messages[0] if result.messages else f"{result.validation_type} validation failed",
            "provider_info": provider_info,  # Include the entire provider_info dict
            "tin": provider_info.get("TIN", "")  # Extract TIN directly for easier access
        }
        
        # Add validation-specific details
        if result.validation_type == "rate":
            # For rate failures, include rate information
            failure_record.update({
                "provider_network": provider_info.get("Provider Network", "Unknown"),
                "rates": result.details.get("results", []),
                "total_expected_rate": result.details.get("total_rate", 0)
            })
            
        elif result.validation_type == "line_items":
            # For line item failures, include comparison details
            failure_record.update({
                "comparison_details": result.details.get("comparison_details", {}),
                "db_line_items": source_data.get("db_line_items", []),
                "hcfa_line_items": source_data.get("hcfa", {}).get("line_items", []) if source_data.get("hcfa") else []
            })
            
        elif result.validation_type == "modifier_check":
            # For modifier failures, include invalid modifiers and line items
            failure_record.update({
                "invalid_modifiers": result.details.get("invalid_modifiers", []),
                "line_items": source_data.get("hcfa", {}).get("line_items", []) if source_data.get("hcfa") else []
            })
            
        elif result.validation_type == "unit_check":
            # For unit check failures, include unit violations
            failure_record.update({
                "violations": result.details.get("details", {}).get("non_ancillary_violations", []) if result.details.get("details") else [],
                "line_items": source_data.get("hcfa", {}).get("line_items", []) if source_data.get("hcfa") else []
            })
            
        # Include raw source data to ensure nothing is lost but avoid duplication
        if "hcfa" not in failure_record and "hcfa" in source_data:
            failure_record["hcfa"] = source_data["hcfa"]
            
        return failure_record

    def _determine_error_code(self, result: ValidationResult) -> str:
        """Map validation failures to standardized error codes."""
        validation_type = result.validation_type.lower()
        if "modifier" in validation_type:
            return ValidationErrorCode.MODIFIER_INVALID
        elif "unit" in validation_type:
            return ValidationErrorCode.UNITS_INVALID
        elif "rate" in validation_type:
            return ValidationErrorCode.RATE_MISMATCH
        elif "bundle" in validation_type:
            return ValidationErrorCode.BUNDLE_ERROR
        elif "line_item" in validation_type:
            return ValidationErrorCode.LINE_ITEM_MISMATCH
        return "UNK_001"

    def log_validation(self, result: ValidationResult):
        """Append validation result to internal list."""
        self.results.append(result)

    def save(self):
        """Save results to separate PASS and FAIL JSON files with simplified failure format."""
        passes, failures = [], []
        failure_types = Counter()

        for r in self.results:
            if r.status == "PASS" and all(v.status == "PASS" for v in self.results if v.file_name == r.file_name):
                passes.append(self._create_pass_record(r))
            else:
                try:
                    failure_record = self._create_failure_record(r)
                    failures.append(failure_record)
                    failure_types[r.validation_type] += 1
                except Exception as e:
                    print(f"Error creating failure record: {e}")
                    # Create a minimal failure record to avoid losing data
                    failures.append({
                        "file_name": r.file_name,
                        "status": "FAIL",
                        "validation_type": r.validation_type,
                        "error": f"Error creating failure record: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })
                    failure_types[r.validation_type] += 1

        # Save to JSON files
        passes_file = self.log_dir / f"validation_passes_{self.timestamp}.json"
        failures_file = self.log_dir / f"validation_failures_{self.timestamp}.json"
        summary_file = self.log_dir / f"validation_summary_{self.timestamp}.json"

        with open(passes_file, "w", encoding="utf-8") as f:
            json.dump(passes, f, indent=2)

        with open(failures_file, "w", encoding="utf-8") as f:
            json.dump(failures, f, indent=2)

        # Create and save summary
        summary = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "total_files": len(passes) + len(failures),
            "passed_files": len(passes),
            "failed_files": len(failures),
            "failure_breakdown": {k: v for k, v in failure_types.most_common()},
            "common_errors": self._analyze_common_errors(failures)
        }

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Print Summary
        print("\n📊 **Validation Session Summary**")
        print(f"Session ID: {self.session_id}")
        print(f"✅ Passed Files: {len(passes)}")
        print(f"❌ Failed Files: {len(failures)}")

        if failures:
            print("\n🔍 **Failure Breakdown:**")
            for failure_type, count in failure_types.most_common():
                print(f"  - {failure_type}: {count} occurrences")

        return {
            "passes_file": passes_file,
            "failures_file": failures_file,
            "summary_file": summary_file
        }

    def _create_pass_record(self, result: ValidationResult) -> Dict[str, Any]:
        """Create a standardized pass record (unchanged from original implementation)."""
        enriched_line_items = []
        for line in result.details.get("results", []):
            enriched_line_items.append({
                "date_of_service": result.date_of_service,
                "cpt": line.get("cpt", ""),
                "modifier": line.get("modifier", ""),
                "units": line.get("units", 1),
                "charge": line.get("charge", "0.00"),
                "validated_rate": line.get("validated_rate", 0)
            })

        return {
            "file_info": {
                "file_name": result.file_name,
                "order_id": result.order_id,
                "timestamp": datetime.now().isoformat(),
                "validation_session_id": self.session_id
            },
            "validation_summary": {
                "status": "PASS",
                "total_checks": len(result.details.get("results", [])),
                "failed_checks": 0
            },
            "data": {
                "patient_info": result.source_data.get("db_patient_info", {}) if result.source_data else {},
                "provider_info": result.source_data.get("db_provider_info", {}) if result.source_data else {},
                "date_of_service": result.date_of_service,
                "line_items": enriched_line_items,
                "comparison_details": result.details.get("comparison_details", {})
            }
        }

    def _analyze_common_errors(self, failures: List[Dict]) -> List[Dict]:
        """Analyze failures to identify common error patterns."""
        error_patterns = Counter()
        for failure in failures:
            error_code = failure.get("error_code", "UNK_001")
            error_patterns[error_code] += 1

        return [
            {
                "error_code": code,
                "count": count,
                "description": ValidationErrorCode.get_description(code)
            }
            for code, count in error_patterns.most_common(5)
        ]