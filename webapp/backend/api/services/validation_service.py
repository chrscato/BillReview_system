import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter

class ValidationService:
    def __init__(self):
        # Update the path to be relative to the backend directory
        self.log_dir = Path(__file__).parent.parent.parent.parent / "logs"
        self.log_dir.mkdir(exist_ok=True)

    def get_all_sessions(self) -> List[Dict]:
        """Retrieve all validation sessions."""
        sessions = []
        for summary_file in self.log_dir.glob("validation_summary_*.json"):
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                sessions.append({
                    'session_id': summary['session_id'],
                    'timestamp': summary['timestamp'],
                    'total_files': summary['total_files'],
                    'passed_files': summary['passed_files'],
                    'failed_files': summary['failed_files']
                })
        return sorted(sessions, key=lambda x: x['timestamp'], reverse=True)

    def get_session_details(self, session_id: str) -> Optional[Dict]:
        """Get detailed information for a specific validation session."""
        for summary_file in self.log_dir.glob("validation_summary_*.json"):
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                if summary['session_id'] == session_id:
                    return summary
        return None

    def get_session_failures(self, session_id: str) -> List[Dict]:
        """Get all failures for a specific validation session."""
        failures = []
        for failures_file in self.log_dir.glob("validation_failures_*.json"):
            with open(failures_file, 'r') as f:
                failure_data = json.load(f)
                session_failures = [
                    failure for failure in failure_data
                    if failure['file_info']['validation_session_id'] == session_id
                ]
                failures.extend(session_failures)
        return failures

    def process_correction(self, failure_id: str, correction_data: Dict) -> Dict:
        """Process and save a correction for a validation failure."""
        # Create correction record
        correction = {
            'failure_id': failure_id,
            'correction_data': correction_data,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }

        # Save correction to database/file
        correction_file = self.log_dir / f"corrections_{failure_id}.json"
        with open(correction_file, 'w') as f:
            json.dump(correction, f, indent=2)

        return {'status': 'success', 'correction_id': str(correction_file)}

    def get_error_statistics(self) -> Dict:
        """Generate statistics about validation errors."""
        error_counts = Counter()
        severity_counts = Counter()
        validation_type_counts = Counter()

        for failures_file in self.log_dir.glob("validation_failures_*.json"):
            with open(failures_file, 'r') as f:
                failures = json.load(f)
                for failure in failures:
                    error_code = failure['failure_details']['error_code']
                    severity = failure['validation_summary']['severity_level']
                    validation_type = failure['validation_summary']['validation_type']

                    error_counts[error_code] += 1
                    severity_counts[severity] += 1
                    validation_type_counts[validation_type] += 1

        return {
            'error_codes': dict(error_counts.most_common(5)),
            'severity_levels': dict(severity_counts),
            'validation_types': dict(validation_type_counts),
            'total_failures': sum(error_counts.values())
        }

    def compare_versions(self, file_id: str) -> Dict:
        """Compare original and corrected versions of a file."""
        # Load original failure
        original = None
        corrected = None

        for failures_file in self.log_dir.glob("validation_failures_*.json"):
            with open(failures_file, 'r') as f:
                failures = json.load(f)
                for failure in failures:
                    if failure['file_info']['file_name'] == file_id:
                        original = failure
                        break

        # Load correction if it exists
        correction_file = self.log_dir / f"corrections_{file_id}.json"
        if correction_file.exists():
            with open(correction_file, 'r') as f:
                corrected = json.load(f)

        return {
            'original': original,
            'corrected': corrected,
            'differences': self._compute_differences(original, corrected) if original and corrected else None
        }

    def _compute_differences(self, original: Dict, corrected: Dict) -> Dict:
        """Compute differences between original and corrected versions."""
        differences = {
            'changed_fields': [],
            'added_fields': [],
            'removed_fields': []
        }

        original_data = original.get('context', {}).get('hcfa_data', {})
        corrected_data = corrected.get('correction_data', {})

        # Compare fields
        for key in set(original_data.keys()) | set(corrected_data.keys()):
            if key in original_data and key in corrected_data:
                if original_data[key] != corrected_data[key]:
                    differences['changed_fields'].append({
                        'field': key,
                        'original': original_data[key],
                        'corrected': corrected_data[key]
                    })
            elif key in original_data:
                differences['removed_fields'].append({
                    'field': key,
                    'original': original_data[key]
                })
            else:
                differences['added_fields'].append({
                    'field': key,
                    'corrected': corrected_data[key]
                })

        return differences 