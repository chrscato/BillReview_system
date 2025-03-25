from typing import Dict, List
import pandas as pd
from utils.helpers import clean_tin, safe_int
from core.services.database import DatabaseService

class RateValidator:
    def __init__(self, conn):
        self.conn = conn
        self.db_service = DatabaseService()

    def validate(self, hcfa_lines: List[Dict], order_id: str) -> Dict:
        """
        Validate rates for CPT codes, including bundled claims.
        Applies unit multiplication to rate calculations.
        """
        rate_results = []
        provider_details = self.db_service.get_provider_details(order_id, self.conn)

        if not provider_details:
            return {
                "status": "FAIL",
                "reason": "Provider details not found",
                "results": [],
                "total_rate": 0
            }

        clean_provider_tin = clean_tin(provider_details['TIN'])
        provider_network = provider_details['Provider Network']

        # Fetch procedure categories
        dim_proc_df = pd.read_sql_query("SELECT proc_cd, proc_category FROM dim_proc", self.conn)
        proc_categories = dict(zip(dim_proc_df['proc_cd'], dim_proc_df['proc_category']))

        has_any_failure = False
        total_rate = 0

        for line in hcfa_lines:
            cpt = str(line.get('cpt', ''))
            units = safe_int(line.get('units', 1))
            
            # Default values if validation fails
            base_rate = None
            unit_adjusted_rate = None
            rate_source = "Unknown"
            
            # ✅ Check if the claim is a bundled CPT case
            if line.get("bundle_type"):
                print(f"Processing bundled rate for {line['bundle_type']}")
                line["validated_rate"] = "BUNDLED"
                rate_results.append({**line, "status": "PASS", "rate_source": "Bundle"})
                continue  # ✅ Skip standard rate validation for bundled claims

            # ✅ Standard rate validation
            if cpt in proc_categories and proc_categories[cpt].lower() == 'ancillary':
                base_rate = 0.00
                unit_adjusted_rate = 0.00
                rate_source = "Ancillary"
                
                result = {
                    **line, 
                    "status": "PASS", 
                    "base_rate": base_rate,
                    "unit_adjusted_rate": unit_adjusted_rate,
                    "units": units,
                    "rate_source": rate_source,
                    "validated_rate": unit_adjusted_rate
                }
                rate_results.append(result)
                continue

            # ✅ PPO Rate check (for all providers)
            ppo_query = "SELECT rate FROM ppo WHERE TRIM(TIN) = ? AND proc_cd = ?"
            ppo_rate = pd.read_sql_query(ppo_query, self.conn, params=[clean_provider_tin, cpt])

            if not ppo_rate.empty:
                base_rate = float(ppo_rate['rate'].iloc[0])
                unit_adjusted_rate = base_rate * units
                rate_source = "PPO"
                
                result = {
                    **line, 
                    "status": "PASS", 
                    "base_rate": base_rate,
                    "unit_adjusted_rate": unit_adjusted_rate,
                    "units": units,
                    "rate_source": rate_source,
                    "validated_rate": unit_adjusted_rate
                }
                rate_results.append(result)
                total_rate += unit_adjusted_rate
                continue

            # ✅ OTA Rate check
            ota_query = "SELECT rate FROM current_otas WHERE ID_Order_PrimaryKey = ? AND CPT = ?"
            ota_rates = pd.read_sql_query(ota_query, self.conn, params=[order_id, cpt])

            if not ota_rates.empty:
                base_rate = float(ota_rates['rate'].iloc[0])
                unit_adjusted_rate = base_rate * units
                rate_source = "OTA"
                
                result = {
                    **line, 
                    "status": "PASS", 
                    "base_rate": base_rate,
                    "unit_adjusted_rate": unit_adjusted_rate,
                    "units": units,
                    "rate_source": rate_source,
                    "validated_rate": unit_adjusted_rate
                }
                rate_results.append(result)
                total_rate += unit_adjusted_rate
                continue
                
            # ✅ If no rate is found, mark as failure
            has_any_failure = True
            rate_results.append({
                **line, 
                "validated_rate": None, 
                "status": "FAIL",
                "base_rate": None,
                "unit_adjusted_rate": None,
                "units": units,
                "rate_source": None,
                "message": f"No rate found for CPT {cpt}"
            })

        # ✅ Determine final rate validation status
        has_failures = any(r["status"] == "FAIL" for r in rate_results)
        
        return {
            "status": "FAIL" if has_failures else "PASS",
            "results": rate_results,
            "total_rate": total_rate,
            "provider_details": provider_details,
            "messages": self._generate_messages(rate_results, total_rate)
        }
    
    def _generate_messages(self, rate_results: List[Dict], total_rate: float) -> List[str]:
        """
        Generate human-readable messages about rate validation results.
        
        Args:
            rate_results: List of rate validation results
            total_rate: Total calculated rate
            
        Returns:
            List[str]: Human-readable messages
        """
        messages = []
        
        # Count rates by source
        rate_sources = {}
        for result in rate_results:
            if result["status"] == "PASS":
                source = result.get("rate_source", "Unknown")
                rate_sources[source] = rate_sources.get(source, 0) + 1
        
        # Count failures
        failures = [r for r in rate_results if r["status"] == "FAIL"]
        
        if not failures:
            source_breakdown = ", ".join([f"{count} from {source}" for source, count in rate_sources.items()])
            messages.append(f"All rates validated successfully. Total rate: ${total_rate:.2f} ({source_breakdown})")
        else:
            messages.append(f"Failed to validate rates for {len(failures)} CPT codes.")
            failure_cpts = ", ".join([f"{r['cpt']}" for r in failures])
            messages.append(f"Missing rates for: {failure_cpts}")
            
            if len(rate_results) > len(failures):
                messages.append(f"Successfully validated {len(rate_results) - len(failures)} CPT codes. Partial total: ${total_rate:.2f}")
        
        return messages