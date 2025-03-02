# core/validators/units.py
from typing import Dict, List
import pandas as pd
from utils.helpers import safe_int

class UnitsValidator:
    def __init__(self, dim_proc_df: pd.DataFrame):
        self.dim_proc_df = dim_proc_df

    def get_proc_category(self, cpt: str) -> str:
        """Get procedure category for CPT code"""
        match = self.dim_proc_df[self.dim_proc_df['proc_cd'] == str(cpt)]
        if match.empty:
            return None
        return match['proc_category'].iloc[0]

    def validate(self, hcfa_data: Dict) -> Dict:
        """Validate units in line items, checking for non-ancillary codes with units > 1"""
        invalid_units = []
        
        for line in hcfa_data.get('line_items', []):
            # Convert units safely to integer
            units = safe_int(line.get('units', 1))
            cpt = str(line.get('cpt', '')).strip()
            proc_category = self.get_proc_category(cpt)
            
            if units > 1:
                is_ancillary = proc_category and proc_category.lower() == "ancillary"
                invalid_units.append({
                    "cpt": cpt,
                    "units": units,
                    "is_ancillary": is_ancillary,
                    "proc_category": proc_category
                })

        # Filter for non-ancillary violations
        non_ancillary_overages = [u for u in invalid_units if not u['is_ancillary']]
        
        return {
            "status": "FAIL" if non_ancillary_overages else "PASS",
            "details": {
                "all_unit_issues": invalid_units,
                "non_ancillary_violations": non_ancillary_overages,
                "total_violations": len(non_ancillary_overages)
            },
            "messages": [
                f"Non-ancillary CPT codes with units > 1 found: {len(non_ancillary_overages)}" if non_ancillary_overages else "No unit violations found"
            ]
        }