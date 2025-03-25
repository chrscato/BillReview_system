# core/validators/units.py
from typing import Dict, List, Set
import pandas as pd
from utils.helpers import safe_int
from config.settings import settings
from config.emg_config import EMG_CONFIGURATIONS

class UnitsValidator:
    """
    Validator for CPT code units.
    Checks if units are valid based on procedure categories and specific code rules.
    """
    
    # Set of CPT codes that can have multiple units regardless of category
    MULTI_UNIT_EXEMPT_CODES = {
        # Time-based codes
        "95910", "95911", "95912", "95913",  # Nerve conduction studies
        "97110", "97112", "97116", "97140", "97530",  # Therapeutic procedures (15-min increments)
        # Other exempt codes that commonly have multiple units
        "76140",  # X-ray consultation
        "96372",  # Therapeutic injection
        "96373",  # Intra-arterial injection
        "96374",  # IV push
    }
    
    # Maximum units allowed for any code (safety limit)
    MAX_ALLOWED_UNITS = 12
    
    def __init__(self, dim_proc_df: pd.DataFrame):
        """
        Initialize the validator with procedure code reference data.
        
        Args:
            dim_proc_df: DataFrame containing procedure codes and categories
        """
        self.dim_proc_df = dim_proc_df
        
        # Extract and cache ancillary procedure codes for faster lookups
        ancillary_rows = dim_proc_df[dim_proc_df['proc_category'].str.lower() == 'ancillary']
        self.ancillary_codes = set(ancillary_rows['proc_cd'].astype(str).tolist())
        
        # Load EMG configurations
        self.emg_bundles = EMG_CONFIGURATIONS["BUNDLES"]
        self.emg_allowed_units = EMG_CONFIGURATIONS["ALLOWED_UNITS"]
    
    def get_proc_category(self, cpt: str) -> str:
        """Get procedure category for CPT code"""
        match = self.dim_proc_df[self.dim_proc_df['proc_cd'] == str(cpt)]
        if match.empty:
            return None
        return match['proc_category'].iloc[0]
    
    def is_emg_code(self, cpt: str) -> bool:
        """Check if a CPT code is part of EMG procedures"""
        return cpt in self.emg_allowed_units
    
    def get_emg_allowed_units(self, cpt: str) -> int:
        """Get allowed units for an EMG code"""
        return self.emg_allowed_units.get(cpt, 1)
    
    def detect_emg_bundle(self, line_items: List[Dict]) -> Dict:
        """
        Detect if the line items form a valid EMG bundle.
        
        Args:
            line_items: List of line items to check
            
        Returns:
            Dict with bundle information
        """
        # Extract CPT codes
        cpt_codes = {str(line.get('cpt', '')) for line in line_items}
        
        # Check each bundle
        for bundle_name, bundle_codes in self.emg_bundles.items():
            # Check if all codes in the bundle are present
            if all(code in cpt_codes for code in bundle_codes):
                return {
                    "found": True,
                    "name": bundle_name,
                    "codes": bundle_codes
                }
        
        # Check if we have any EMG codes even if not a complete bundle
        emg_codes = [code for code in cpt_codes if self.is_emg_code(code)]
        if emg_codes:
            return {
                "found": False,
                "name": None,
                "codes": emg_codes,
                "message": "Contains EMG codes but not a recognized bundle"
            }
        
        # No EMG codes found
        return {
            "found": False,
            "name": None,
            "codes": []
        }

    def validate(self, hcfa_data: Dict) -> Dict:
        """
        Validate units in line items, checking for non-ancillary codes with units > 1
        and other unit validation rules. Special handling for EMG bundles.
        """
        line_items = hcfa_data.get('line_items', [])
        
        # First check for EMG bundles
        emg_bundle = self.detect_emg_bundle(line_items)
        is_emg_bundle = emg_bundle["found"]
        
        invalid_units = []
        
        for line in line_items:
            # Convert units safely to integer
            units = safe_int(line.get('units', 1))
            cpt = str(line.get('cpt', '')).strip()
            proc_category = self.get_proc_category(cpt)
            
            # EMG-specific validation
            if self.is_emg_code(cpt):
                allowed_units = self.get_emg_allowed_units(cpt)
                if units > allowed_units:
                    invalid_units.append({
                        "cpt": cpt,
                        "units": units,
                        "is_ancillary": False,
                        "proc_category": proc_category,
                        "allowed_units": allowed_units,
                        "type": "emg",
                        "message": f"EMG code {cpt} exceeds allowed units of {allowed_units}"
                    })
                continue
            
            # Standard validation
            if units > 1:
                is_ancillary = proc_category and proc_category.lower() == "ancillary"
                is_exempt = cpt in self.MULTI_UNIT_EXEMPT_CODES
                
                if not is_ancillary and not is_exempt:
                    invalid_units.append({
                        "cpt": cpt,
                        "units": units,
                        "is_ancillary": is_ancillary,
                        "proc_category": proc_category,
                        "type": "standard",
                        "message": f"Non-ancillary code {cpt} should not have multiple units"
                    })

        # Filter for non-ancillary violations
        non_ancillary_overages = [u for u in invalid_units if u['type'] == 'standard']
        emg_violations = [u for u in invalid_units if u['type'] == 'emg']
        
        # Generate appropriate messages
        messages = []
        if non_ancillary_overages:
            messages.append(f"Non-ancillary CPT codes with units > 1 found: {len(non_ancillary_overages)}")
        
        if emg_violations:
            messages.append(f"EMG codes with units exceeding limits found: {len(emg_violations)}")
        
        if is_emg_bundle:
            messages.append(f"Valid EMG bundle detected: {emg_bundle['name']}")
        elif emg_bundle["codes"]:
            messages.append(f"Partial EMG codes detected but not a valid bundle")
        
        if not invalid_units:
            messages.append("No unit violations found")
        
        return {
            "status": "FAIL" if invalid_units else "PASS",
            "details": {
                "all_unit_issues": invalid_units,
                "non_ancillary_violations": non_ancillary_overages,
                "emg_violations": emg_violations,
                "total_violations": len(invalid_units),
                "emg_bundle": emg_bundle if emg_bundle["codes"] else None
            },
            "messages": messages
        }