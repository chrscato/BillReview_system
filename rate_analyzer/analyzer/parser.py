"""
Parser module for extracting rate validation failures from JSON files.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pandas as pd

class ValidationFailureParser:
    """Parser for validation failure JSON files."""
    
    def __init__(self):
        self.raw_data = []
        self.rate_failures = []
        self.file_path = None
    
    def load_file(self, file_path: Union[str, Path]) -> bool:
        """
        Load a validation failure JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            bool: True if file was loaded successfully, False otherwise
        """
        self.file_path = Path(file_path)
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.raw_data = json.load(f)
                
            # Print basic info about the loaded data
            if isinstance(self.raw_data, list):
                print(f"Loaded JSON array with {len(self.raw_data)} items")
                # Check first few items to understand the structure
                if len(self.raw_data) > 0:
                    first_item = self.raw_data[0]
                    if isinstance(first_item, dict):
                        keys = list(first_item.keys())
                        print(f"First item keys: {', '.join(keys[:5])}{'...' if len(keys) > 5 else ''}")
                        
                        # Check if this is a rate validation failure
                        if 'validation_summary' in first_item:
                            validation_type = first_item.get('validation_summary', {}).get('validation_type')
                            print(f"Validation type in first item: {validation_type}")
            else:
                print(f"Loaded JSON data type: {type(self.raw_data)}")
                
            return True
        except Exception as e:
            print(f"Error loading file {file_path}: {str(e)}")
            return False
            
    def _detect_format(self) -> str:
        """
        Detect the format of the validation failures JSON.
        
        Returns:
            str: Format type ('standard', 'alternate', 'unknown')
        """
        if not self.raw_data:
            return 'unknown'
            
        if not isinstance(self.raw_data, list):
            return 'unknown'
            
        if len(self.raw_data) == 0:
            return 'unknown'
            
        # Check first item
        first_item = self.raw_data[0]
        
        if not isinstance(first_item, dict):
            return 'unknown'
            
        # Check for standard format (with validation_summary)
        if 'validation_summary' in first_item and 'file_info' in first_item:
            return 'standard'
            
        # Check for alternate format
        if 'status' in first_item and 'details' in first_item and 'validation_type' in first_item:
            return 'alternate'
            
        return 'unknown'
    
    def extract_rate_failures(self) -> List[Dict]:
        """
        Extract rate validation failures from the loaded data.
        
        Returns:
            List[Dict]: List of rate validation failures
        """
        if not self.raw_data:
            return []
        
        # Reset rate failures
        self.rate_failures = []
        
        # Extract rate validation failures
        for item in self.raw_data:
            try:
                # Check if we have a valid dictionary
                if not isinstance(item, dict):
                    continue
                    
                # Get validation summary, handle None case
                validation_summary = item.get('validation_summary')
                if not validation_summary or not isinstance(validation_summary, dict):
                    continue
                    
                # Check if this is a rate validation failure
                validation_type = validation_summary.get('validation_type')
                status = validation_summary.get('status')
                
                # Debug info
                if validation_type == 'rate':
                    print(f"Found rate validation: Status={status}")
                
                if validation_type == 'rate' and status == 'FAIL':
                    # Extract relevant information
                    failure_details = self._extract_failure_details(item)
                    if failure_details:
                        self.rate_failures.append(failure_details)
            except Exception as e:
                print(f"Error processing failure item: {str(e)}")
        
        print(f"Extracted {len(self.rate_failures)} rate validation failures")
        return self.rate_failures
    
    def _extract_failure_details(self, failure_item: Dict) -> Dict:
        """
        Extract detailed information from a rate validation failure.
        
        Args:
            failure_item: A failure item from the JSON
            
        Returns:
            Dict: Extracted details or empty dict if extraction failed
        """
        try:
            # Make sure we have a dictionary
            if not isinstance(failure_item, dict):
                print(f"Warning: failure_item is not a dictionary: {type(failure_item)}")
                return {}
                
            # File information
            file_info = failure_item.get('file_info', {}) or {}
            
            # Context information (contains HCFA and reference data)
            context = failure_item.get('context', {}) or {}
            hcfa_data = context.get('hcfa_data', {}) or {}
            reference_data = context.get('reference_data', {}) or {}
            provider_info = reference_data.get('provider_info', {}) or {}
            patient_info = reference_data.get('patient_info', {}) or {}
            
            # Special handling for line items which may have different formats
            line_items = []
            if 'line_items' in hcfa_data and isinstance(hcfa_data['line_items'], list):
                line_items = hcfa_data['line_items']
            
            # Get failure details
            failure_details = failure_item.get('failure_details', {}) or {}
            
            # Construct a clean failure record with the most relevant information
            return {
                # File and order information
                'file_name': file_info.get('file_name', ''),
                'order_id': file_info.get('order_id', ''),
                'timestamp': file_info.get('timestamp', ''),
                
                # Patient information
                'patient_name': hcfa_data.get('patient_name', ''),
                'date_of_service': hcfa_data.get('date_of_service', ''),
                
                # Provider information
                'provider_name': provider_info.get('DBA Name Billing Name', ''),
                'provider_tin': provider_info.get('TIN', ''),
                'provider_npi': provider_info.get('NPI', ''),
                'provider_network': provider_info.get('Provider Network', ''),
                
                # Billing information
                'billing_tin': hcfa_data.get('billing_provider_tin', ''),
                'total_charge': hcfa_data.get('total_charge', ''),
                
                # Line items
                'line_items': line_items,
                
                # Failure details
                'error_code': failure_details.get('error_code', ''),
                'error_message': failure_details.get('error_message', ''),
                'error_description': failure_details.get('error_description', ''),
                'suggestion': failure_details.get('suggestion', '')
            }
        except Exception as e:
            print(f"Error extracting failure details: {str(e)}")
            return {}
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert rate failures to a pandas DataFrame.
        
        Returns:
            pd.DataFrame: DataFrame containing failure information
        """
        if not self.rate_failures:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'file_name', 'order_id', 'timestamp', 'patient_name', 'date_of_service',
                'provider_name', 'provider_tin', 'provider_npi', 'provider_network',
                'billing_tin', 'total_charge', 'cpt', 'modifier', 'units', 'charge',
                'error_code', 'error_message', 'error_description', 'suggestion'
            ])
        
        # Create a list to hold flattened records
        flattened_records = []
        
        # Process each rate failure
        for failure in self.rate_failures:
            # Safety check - make sure we have a dictionary
            if not isinstance(failure, dict):
                continue
                
            # Get line items safely
            line_items = failure.get('line_items', []) or []
            
            # If no line items, add a record with just the failure info
            if not line_items:
                failure_copy = failure.copy()
                if 'line_items' in failure_copy:
                    failure_copy.pop('line_items')
                # Add placeholder values for line item fields
                failure_copy['cpt'] = ''
                failure_copy['modifier'] = ''
                failure_copy['units'] = 1
                failure_copy['charge'] = '0.00'
                flattened_records.append(failure_copy)
                continue
            
            # For each line item, create a separate record
            for line_item in line_items:
                # Skip if not a dictionary
                if not isinstance(line_item, dict):
                    continue
                    
                record = {**failure.copy()}
                if 'line_items' in record:
                    record.pop('line_items')
                
                # Add line item details
                record['cpt'] = line_item.get('cpt', '')
                record['modifier'] = line_item.get('modifier', '')
                
                # Handle units (could be string or int)
                try:
                    record['units'] = int(line_item.get('units', 1))
                except (ValueError, TypeError):
                    record['units'] = 1
                
                # Handle charge (could be string or float)
                try:
                    record['charge'] = float(line_item.get('charge', '0.00').replace(',', '')
                                            if isinstance(line_item.get('charge'), str)
                                            else line_item.get('charge', 0.00))
                except (ValueError, TypeError):
                    record['charge'] = 0.00
                
                flattened_records.append(record)
        
        # Create DataFrame
        df = pd.DataFrame(flattened_records)
        
        # Fill missing values
        df = df.fillna('')
        
        # Convert numeric columns properly
        if 'charge' in df.columns:
            df['charge'] = pd.to_numeric(df['charge'], errors='coerce').fillna(0.0)
        if 'units' in df.columns:
            df['units'] = pd.to_numeric(df['units'], errors='coerce').fillna(1).astype(int)
        if 'total_charge' in df.columns:
            df['total_charge'] = pd.to_numeric(df['total_charge'].astype(str).str.replace(',', ''), 
                                              errors='coerce').fillna(0.0)
        
        print(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
        return df
    
    @staticmethod
    def get_latest_file(directory_path: Union[str, Path]) -> Optional[Path]:
        """
        Get the latest validation failures JSON file from a directory.
        
        Args:
            directory_path: Path to the directory containing JSON files
            
        Returns:
            Optional[Path]: Path to the latest JSON file or None if no files found
        """
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            return None
        
        # Find all JSON files that contain 'validation_failures' in the name
        json_files = list(directory.glob('*validation_failures*.json'))
        if not json_files:
            return None
        
        # Sort by modification time (newest last)
        json_files.sort(key=lambda f: f.stat().st_mtime)
        
        # Return the newest file
        return json_files[-1]