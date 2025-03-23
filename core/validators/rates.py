from typing import Dict, List
import pandas as pd
from utils.helpers import clean_tin
from core.services.database import DatabaseService

class RateValidator:
    def __init__(self, conn):
        self.conn = conn
        self.db_service = DatabaseService()

    def validate(self, hcfa_lines: List[Dict], order_id: str) -> Dict:
        """Validate rates for CPT codes, including bundled claims."""
        rate_results = []
        provider_details = self.db_service.get_provider_details(order_id, self.conn)

        if not provider_details:
            return {
                "status": "FAIL",
                "reason": "Provider details not found",
                "results": []
            }

        clean_provider_tin = clean_tin(provider_details['TIN'])
        provider_network = provider_details['Provider Network']

        # Fetch procedure categories
        dim_proc_df = pd.read_sql_query("SELECT proc_cd, proc_category FROM dim_proc", self.conn)
        proc_categories = dict(zip(dim_proc_df['proc_cd'], dim_proc_df['proc_category']))

        has_any_failure = False

        for line in hcfa_lines:
            cpt = str(line.get('cpt', ''))

            # ✅ Check if the claim is a bundled CPT case
            if line.get("bundle_type"):
                print(f"Processing bundled rate for {line['bundle_type']}")
                line["validated_rate"] = "BUNDLED"
                rate_results.append({**line, "status": "PASS"})
                continue  # ✅ Skip standard rate validation for bundled claims

            # ✅ Standard rate validation
            if cpt in proc_categories and proc_categories[cpt].lower() == 'ancillary':
                line["validated_rate"] = 0.00
                rate_results.append({**line, "status": "PASS"})
                continue

            # ✅ PPO Rate check (for all providers)
            ppo_query = "SELECT rate FROM ppo WHERE TRIM(TIN) = ? AND proc_cd = ?"
            ppo_rate = pd.read_sql_query(ppo_query, self.conn, params=[clean_provider_tin, cpt])

            if not ppo_rate.empty:
                line["validated_rate"] = float(ppo_rate['rate'].iloc[0])
                rate_results.append({**line, "status": "PASS"})
                continue

            # ✅ OTA Rate check
            ota_query = "SELECT rate FROM current_otas WHERE ID_Order_PrimaryKey = ? AND CPT = ?"
            ota_rates = pd.read_sql_query(ota_query, self.conn, params=[order_id, cpt])

            if not ota_rates.empty:
                line["validated_rate"] = float(ota_rates['rate'].iloc[0])
                rate_results.append({**line, "status": "PASS"})
                continue

            # ✅ If no rate is found, mark as failure
            has_any_failure = True
            rate_results.append({**line, "validated_rate": None, "status": "FAIL"})

        # ✅ Determine final rate validation status
        has_failures = any(r["status"] == "FAIL" for r in rate_results)
        total_rate = sum(r["validated_rate"] or 0 for r in rate_results if isinstance(r["validated_rate"], (int, float)))

        return {
            "status": "FAIL" if has_failures else "PASS",
            "results": rate_results,
            "total_rate": total_rate,
            "provider_details": provider_details
        }
