from typing import Dict, List, Set
import pandas as pd
import json
from pathlib import Path

BUNDLED_CPT_FILE = Path(__file__).parent.parent.parent / "config" / "bundled_cpts.json"

class LineItemValidator:
    def __init__(self, dim_proc_df: pd.DataFrame):
        self.dim_proc_df = dim_proc_df
        self.bundled_cpts = self.load_bundled_cpts()

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

        # STEP 1: Perform exact match check first (simplest case)
        if hcfa_codes == order_codes:
            return {
                "status": "PASS",
                "match_type": "exact_match",
                "codes": list(hcfa_codes),
                "message": "Exact match found."
            }

        # STEP 2: Build mapping of line items for reference
        line_item_mapping = {}
        for hcfa_line in filtered_hcfa_lines:
            hcfa_cpt = str(hcfa_line['cpt'])
            matching_lines = order_lines[order_lines['CPT'] == hcfa_cpt]
            if not matching_lines.empty:
                line_item_mapping[hcfa_cpt] = matching_lines['id'].tolist()

        # STEP 3: Build category mappings with validation
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

        # STEP 4: If we have category issues, report them as failures first
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

        # STEP 5: Perform category-based validation for non-ancillary codes
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

        # STEP 6: If we get here, categories match but not exact codes - this is a pass
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