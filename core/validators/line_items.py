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
        """Get procedure category from dim_proc"""
        match = self.dim_proc_df[self.dim_proc_df['proc_cd'] == str(cpt)]
        if match.empty:
            return None
        return match['proc_category'].iloc[0]


    def check_bundled_cpts(self, hcfa_cpts: Set[str], order_cpts: Set[str]) -> Dict:
        """Ensure HCFA and Order CPTs belong to the same bundle and have no extra codes."""
        combined_cpts = hcfa_cpts | order_cpts  # Combine HCFA & Order CPTs

        for bundle_type, required_cpts in self.bundled_cpts.items():
            required_set = set(required_cpts)

            # ✅ Ensure both HCFA and Order contain at least one CPT from the bundle
            if not hcfa_cpts.intersection(required_set) or not order_cpts.intersection(required_set):
                continue  # Skip if neither side contains part of the bundle

            # ✅ Fail if there are CPTs outside of the detected bundle
            if combined_cpts - required_set:
                return {
                    "status": "FAIL",
                    "reason": f"Order contains CPT codes outside the detected {bundle_type} bundle.",
                    "unexpected_cpts": list(combined_cpts - required_set),
                    "message": "Unexpected CPT codes detected in order. Validation failed."
                }

            # ✅ Allow minor mismatches but flag them for review
            missing_cpts = required_set - combined_cpts
            return {
                "status": "BUNDLED",
                "bundle_type": bundle_type,
                "message": f"Order identified as {bundle_type} bundle.",
                "missing_cpts": list(missing_cpts),
                "note": "Minor CPT mismatches found but proceeding."
            }

        return None  # No valid bundle found

    def validate(self, hcfa_lines: List[Dict], order_lines: pd.DataFrame) -> Dict:
        """Validate CPT codes, handling both bundled and standard cases."""
        filtered_hcfa_lines = [
            line for line in hcfa_lines 
            if str(line['cpt']) not in {"51655"}
        ]

        hcfa_codes = set(str(line['cpt']) for line in filtered_hcfa_lines)
        order_codes = set(str(line['CPT']) for _, line in order_lines.iterrows())

        # ✅ STEP 1: Check for bundled claim FIRST
        bundled_result = self.check_bundled_cpts(hcfa_codes, order_codes)
        if bundled_result:
            return bundled_result  # Proceed only if no unrelated CPTs exist

        # ✅ STEP 2: Perform Standard Line Item Validation (Exact Match Check)
        if hcfa_codes == order_codes:
            return {
                "status": "PASS",
                "match_type": "exact_match",
                "codes": list(hcfa_codes),
                "message": "Exact match found."
            }

        # ✅ STEP 3: Perform Category-Based Validation (If No Exact Match)
        line_item_mapping = {}
        for hcfa_line in filtered_hcfa_lines:
            hcfa_cpt = str(hcfa_line['cpt'])
            matching_lines = order_lines[order_lines['CPT'] == hcfa_cpt]
            if not matching_lines.empty:
                line_item_mapping[hcfa_cpt] = matching_lines['id'].tolist()

        hcfa_categories = {}
        ancillary_codes = set()
        for line in filtered_hcfa_lines:
            cpt = line['cpt']
            cat = self.get_proc_category(cpt)
            if cat:
                hcfa_categories[cpt] = cat
                if cat.lower() == "ancillary":
                    ancillary_codes.add(cpt)

        order_categories = {}
        for _, line in order_lines.iterrows():
            cpt = line['CPT']
            cat = self.get_proc_category(cpt)
            if cat:
                order_categories[cpt] = cat

        comparison_details = {
            "hcfa_codes": list(hcfa_codes),
            "order_codes": list(order_codes),
            "hcfa_categories": hcfa_categories,
            "order_categories": order_categories
        }

        # ✅ STEP 4: If categories match, mark as a category match pass
        non_ancillary_hcfa = [cat for cpt, cat in hcfa_categories.items() if cpt not in ancillary_codes]
        non_ancillary_order = [cat for cpt, cat in order_categories.items() if cpt not in ancillary_codes]

        hcfa_category_counts = {}
        for cat in non_ancillary_hcfa:
            hcfa_category_counts[cat] = hcfa_category_counts.get(cat, 0) + 1

        order_category_counts = {}
        for cat in non_ancillary_order:
            order_category_counts[cat] = order_category_counts.get(cat, 0) + 1

        for cat, count in hcfa_category_counts.items():
            if cat not in order_category_counts or order_category_counts[cat] < count:
                return {
                    "status": "FAIL",
                    "reason": f"Category '{cat}' count mismatch (HCFA: {count}, Orders: {order_category_counts.get(cat, 0)})",
                    "comparison_details": comparison_details
                }
            order_category_counts[cat] -= count

        return {
            "status": "PASS",
            "match_type": "category_match",
            "categories": list(set(non_ancillary_hcfa)),
            "line_item_mapping": line_item_mapping,
            "comparison_details": comparison_details
        }
