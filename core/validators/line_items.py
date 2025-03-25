from typing import Dict, List, Set
import pandas as pd
import json
from pathlib import Path

BUNDLED_CPT_FILE = Path(__file__).parent.parent.parent / "config" / "bundled_cpts.json"

from typing import Dict, List, Set
import pandas as pd
import json
from pathlib import Path

BUNDLED_CPT_FILE = Path(__file__).parent.parent.parent / "config" / "bundled_cpts.json"

class LineItemValidator:
    def __init__(self, dim_proc_df: pd.DataFrame):
        self.dim_proc_df = dim_proc_df
        self.bundled_cpts = self.load_bundled_cpts()
        
        # EMG procedure codes
        self.emg_study_codes = {"95907", "95908", "95909", "95910", "95911", "95912", "95913"}
        self.emg_needle_codes = {"95885", "95886", "95887"}
        self.emg_eval_codes = {"99203", "99204", "99205"}

    def load_bundled_cpts(self) -> Dict[str, List[str]]:
        """Load the CPT bundle definitions from JSON."""
        if not BUNDLED_CPT_FILE.exists():
            raise FileNotFoundError(f"Bundled CPT JSON not found: {BUNDLED_CPT_FILE}")

        with open(BUNDLED_CPT_FILE, "r") as f:
            return json.load(f)
        
    def get_proc_category(self, cpt: str) -> str:
        """Get procedure category from dim_proc with improved error handling."""
        match = self.dim_proc_df[self.dim_proc_df['proc_cd'] == str(cpt)]
        if match.empty:
            print(f"Warning: CPT code {cpt} not found in dim_proc")
            return None
        
        category = match['proc_category'].iloc[0]
        if not category or category == "0" or str(category).strip() == "":
            print(f"Warning: CPT code {cpt} has invalid category: '{category}'")
        
        return category

    def check_for_emg_package(self, hcfa_codes: Set[str], order_codes: Set[str]) -> Dict:
        """
        Check if this appears to be an EMG package with expected code variations.
        EMG packages often have different codes between HCFA and reference data.
        
        Args:
            hcfa_codes: Set of CPT codes in the HCFA
            order_codes: Set of CPT codes in the order data
            
        Returns:
            Dict with EMG package information
        """
        # Check for EMG codes in HCFA
        hcfa_study_codes = hcfa_codes.intersection(self.emg_study_codes)
        hcfa_needle_codes = hcfa_codes.intersection(self.emg_needle_codes)
        
        # Check for EMG codes in order
        order_study_codes = order_codes.intersection(self.emg_study_codes)
        order_needle_codes = order_codes.intersection(self.emg_needle_codes)
        
        # Determine if this is an EMG package
        is_emg_package = False
        message = ""
        
        # Case 1: Valid EMG package - has both study and needle components in HCFA
        if hcfa_study_codes and hcfa_needle_codes:
            is_emg_package = True
            message = f"EMG package with study ({', '.join(hcfa_study_codes)}) and needle ({', '.join(hcfa_needle_codes)})"
            
            # Subcases to provide more details
            if not order_study_codes and order_needle_codes:
                message += " - Order is missing study codes"
            elif order_study_codes and not order_needle_codes:
                message += " - Order is missing needle codes"
            elif order_study_codes != hcfa_study_codes:
                message += " - Study code mismatch (expected variation)"
        
        # Case 2: Only EMG needle codes
        elif hcfa_needle_codes and not hcfa_study_codes:
            # If we have at least one EMG needle code in both HCFA and order, consider it a match
            if order_needle_codes:
                is_emg_package = True
                message = f"EMG needle codes only ({', '.join(hcfa_needle_codes)})"
        
        # Case 3: Only EMG study codes
        elif hcfa_study_codes and not hcfa_needle_codes:
            # If we have at least one EMG study code in both HCFA and order, consider it a match
            if order_study_codes:
                is_emg_package = True
                message = f"EMG study codes only ({', '.join(hcfa_study_codes)})"
        
        return {
            "is_emg_package": is_emg_package,
            "hcfa_study_codes": list(hcfa_study_codes),
            "hcfa_needle_codes": list(hcfa_needle_codes),
            "order_study_codes": list(order_study_codes),
            "order_needle_codes": list(order_needle_codes),
            "message": message
        }

    def validate(self, hcfa_lines: List[Dict], order_lines: pd.DataFrame) -> Dict:
        #"""Validate CPT codes, with enhanced category validation."""
        # Filter out unacceptable CPT codes
        filtered_hcfa_lines = [
            line for line in hcfa_lines 
            if str(line['cpt']) not in {"51655"}
        ]

        # Extract CPT codes from HCFA and order data
        hcfa_codes = set(str(line['cpt']) for line in filtered_hcfa_lines)
        order_codes = set(str(line['CPT']) for _, line in order_lines.iterrows())
        
        # STEP 1: Check for EMG packages first
        emg_info = self.check_for_emg_package(hcfa_codes, order_codes)
        if emg_info["is_emg_package"]:
            print(f"EMG package detected: {emg_info['message']}")
            
            # Build category mappings for inclusion in the result
            hcfa_categories = {}
            order_categories = {}
            
            for line in filtered_hcfa_lines:
                cpt = str(line['cpt'])
                cat = self.get_proc_category(cpt)
                hcfa_categories[cpt] = cat or "unknown"
                
            for _, line in order_lines.iterrows():
                cpt = str(line['CPT'])
                cat = self.get_proc_category(cpt)
                order_categories[cpt] = cat or "unknown"
            
            return {
                "status": "PASS",
                "match_type": "emg_package_match",
                "codes": list(hcfa_codes),
                "message": f"EMG package detected: {emg_info['message']}",
                "comparison_details": {
                    "hcfa_codes": list(hcfa_codes),
                    "order_codes": list(order_codes),
                    "hcfa_categories": hcfa_categories,
                    "order_categories": order_categories,
                    "emg_info": emg_info
                }
            }

        # STEP 2: Perform exact match check (simplest case)
        if hcfa_codes == order_codes:
            return {
                "status": "PASS",
                "match_type": "exact_match",
                "codes": list(hcfa_codes),
                "message": "Exact match found."
            }

        # STEP 3: Build mapping of line items for reference
        line_item_mapping = {}
        for hcfa_line in filtered_hcfa_lines:
            hcfa_cpt = str(hcfa_line['cpt'])
            matching_lines = order_lines[order_lines['CPT'] == hcfa_cpt]
            if not matching_lines.empty:
                line_item_mapping[hcfa_cpt] = matching_lines['id'].tolist()

        # STEP 4: Build category mappings with validation
        hcfa_categories = {}
        invalid_categories = []
        ancillary_codes = set()
        
        for line in filtered_hcfa_lines:
            cpt = str(line['cpt'])
            cat = self.get_proc_category(cpt)
            
            # Check for invalid/missing categories
            if not cat or cat == "0" or cat.strip() == "":
                invalid_categories.append({
                    "cpt": cpt,
                    "source": "hcfa",
                    "category": cat,
                    "reason": "Missing or invalid category"
                })
            
            hcfa_categories[cpt] = cat or "unknown"
            if cat and cat.lower() == "ancillary":
                ancillary_codes.add(cpt)

        order_categories = {}
        for _, line in order_lines.iterrows():
            cpt = str(line['CPT'])
            cat = self.get_proc_category(cpt)
            
            # Check for invalid/missing categories
            if not cat or cat == "0" or cat.strip() == "":
                invalid_categories.append({
                    "cpt": cpt,
                    "source": "order",
                    "category": cat,
                    "reason": "Missing or invalid category"
                })
            
            order_categories[cpt] = cat or "unknown"

        # STEP 5: If we have category issues, report them as failures first
        if invalid_categories:
            return {
                "status": "FAIL",
                "reason": "Missing or invalid procedure categories",
                "invalid_categories": invalid_categories,
                "comparison_details": {
                    "hcfa_codes": list(hcfa_codes),
                    "order_codes": list(order_codes),
                    "hcfa_categories": hcfa_categories,
                    "order_categories": order_categories
                },
                "message": f"Found {len(invalid_categories)} CPT codes with missing or invalid categories",
                "resolution_steps": [
                    "Update dim_proc table with valid categories for these CPT codes",
                    "Verify CPT codes are correctly entered",
                    "Check for typos in procedure codes"
                ]
            }

        # STEP 6: Perform category-based validation for non-ancillary codes
        non_ancillary_hcfa = [cat for cpt, cat in hcfa_categories.items() if cpt not in ancillary_codes]
        non_ancillary_order = [cat for cpt, cat in order_categories.items() if cpt not in ancillary_codes]

        hcfa_category_counts = {}
        for cat in non_ancillary_hcfa:
            hcfa_category_counts[cat] = hcfa_category_counts.get(cat, 0) + 1

        order_category_counts = {}
        for cat in non_ancillary_order:
            order_category_counts[cat] = order_category_counts.get(cat, 0) + 1

        # Check category counts
        category_mismatches = []
        for cat, count in hcfa_category_counts.items():
            if cat not in order_category_counts or order_category_counts[cat] < count:
                # Find specific CPT codes involved in the mismatch
                hcfa_cpts = [cpt for cpt, c in hcfa_categories.items() if c == cat]
                order_cpts = [cpt for cpt, c in order_categories.items() if c == cat]
                
                # Skip EMG category mismatches since we handle those separately
                if cat.upper() == "EMG":
                    print(f"EMG category mismatch detected but not treated as failure")
                    continue
                
                category_mismatches.append({
                    "category": cat,
                    "hcfa_count": count,
                    "order_count": order_category_counts.get(cat, 0),
                    "difference": count - order_category_counts.get(cat, 0),
                    "hcfa_cpts": hcfa_cpts,
                    "order_cpts": order_cpts
                })

        if category_mismatches:
            return {
                "status": "FAIL",
                "reason": "Category count mismatch",
                "mismatches": category_mismatches,
                "comparison_details": {
                    "hcfa_codes": list(hcfa_codes),
                    "order_codes": list(order_codes),
                    "hcfa_categories": hcfa_categories,
                    "order_categories": order_categories
                },
                "message": f"Found {len(category_mismatches)} category mismatches between HCFA and order data."
            }

        # STEP 7: If we get here, categories match but not exact codes - this is a pass
        return {
            "status": "PASS",
            "match_type": "category_match",
            "categories": list(set(non_ancillary_hcfa)),
            "line_item_mapping": line_item_mapping,
            "comparison_details": {
                "hcfa_codes": list(hcfa_codes),
                "order_codes": list(order_codes),
                "hcfa_categories": hcfa_categories,
                "order_categories": order_categories
            }
        }