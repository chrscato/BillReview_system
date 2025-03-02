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

    def _create_enhanced_failure_record(self, result: ValidationResult) -> Dict[str, Any]:
        """Create a detailed failure record with enhanced debugging information."""
        error_code = self._determine_error_code(result)
        
        return {
            "file_info": {
                "file_name": result.file_name,
                "order_id": result.order_id,
                "timestamp": datetime.now().isoformat(),
                "validation_session_id": self.session_id
            },
            "validation_summary": {
                "status": result.status,
                "validation_type": result.validation_type,
                "severity_level": self._determine_severity(result),
                "total_checks": len(result.details.get("results", [])) if hasattr(result, "details") else 0,
                "failed_checks": sum(1 for r in result.details.get("results", []) 
                                   if r.get("status") == "FAIL") if hasattr(result, "details") else 1
            },
            "failure_details": {
                "validation_step": result.validation_type,
                "error_code": error_code,
                "error_message": result.messages[0] if result.messages else "Validation failed",
                "error_description": ValidationErrorCode.get_description(error_code),
                "expected_value": result.details.get("expected", "N/A"),
                "actual_value": result.details.get("actual", "N/A"),
                "suggestion": self._generate_suggestion(result)
            },
            "context": {
                "hcfa_data": result.source_data.get("hcfa", {}),
                "reference_data": {
                    "provider_info": result.source_data.get("db_provider_info", {}),
                    "patient_info": result.source_data.get("db_patient_info", {})
                },
                "comparison_details": result.details.get("comparison_details", {})
            }
        }

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

    def _determine_severity(self, result: ValidationResult) -> str:
        """Determine the severity level of the validation failure."""
        if result.validation_type in ["rate", "line_items"]:
            return "ERROR"
        elif result.validation_type in ["modifier", "units"]:
            return "WARNING"
        return "INFO"

    def _generate_suggestion(self, result: ValidationResult) -> str:
        """Generate user-friendly suggestions for fixing the validation error."""
        validation_type = result.validation_type.lower()
        if "modifier" in validation_type:
            return "Review modifier usage and ensure compatibility with procedure code."
        elif "unit" in validation_type:
            return "Check unit count against procedure code guidelines."
        elif "rate" in validation_type:
            return "Verify rate calculation and provider network status."
        elif "bundle" in validation_type:
            return "Review bundle configuration and component procedures."
        return "Review validation details and compare with reference data."

    def log_validation(self, result: ValidationResult):
        """Append validation result to internal list with enhanced tracking."""
        self.results.append(result)

    def save(self):
        """Save results to separate PASS and FAIL JSON files with enhanced error tracking."""
        passes, failures = [], []
        failure_types = Counter()

        for r in self.results:
            if r.status == "PASS" and all(v.status == "PASS" for v in self.results if v.file_name == r.file_name):
                passes.append(self._create_pass_record(r))
            else:
                failure_record = self._create_enhanced_failure_record(r)
                failures.append(failure_record)
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
        """Create a standardized pass record."""
        enriched_line_items = []
        for line in result.details.get("results", []):
            enriched_line_items.append({
                "date_of_service": result.date_of_service,
                "cpt": line["cpt"],
                "modifier": line.get("modifier"),
                "units": line.get("units"),
                "charge": line.get("charge"),
                "validated_rate": line["validated_rate"]
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
                "patient_info": result.source_data.get("db_patient_info", {}),
                "provider_info": result.source_data.get("db_provider_info", {}),
                "date_of_service": result.date_of_service,
                "line_items": enriched_line_items,
                "comparison_details": result.details.get("comparison_details", {})
            }
        }

    def _analyze_common_errors(self, failures: List[Dict]) -> List[Dict]:
        """Analyze failures to identify common error patterns."""
        error_patterns = Counter()
        for failure in failures:
            error_code = failure["failure_details"]["error_code"]
            error_patterns[error_code] += 1

        return [
            {
                "error_code": code,
                "count": count,
                "description": ValidationErrorCode.get_description(code)
            }
            for code, count in error_patterns.most_common(5)
        ]