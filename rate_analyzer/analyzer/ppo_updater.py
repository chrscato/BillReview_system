"""
PPO database updater for rate validation fixes.
"""
import os
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any

class PPOUpdater:
    """
    Class to update PPO rates in the database, either individually or by category.
    """
    
    # Category to procedure code mapping
    PROCEDURE_CATEGORIES = {
        "MRI w/o": ["74181", "70551", "72141", "71550", "73721", "73718", "72148", "70540", "72195", "72146", "73221", "73218"],
        "MRI w/": ["74182", "70552", "72142", "71551", "73722", "73719", "72149", "70542", "72196", "72147", "73222", "73219"],
        "MRI w/&w/o": ["74183", "70553", "72156", "71552", "73723", "73720", "72158", "70543", "72197", "72157", "73223", "73220"],
        "CT w/o": ["74176", "74150", "72125", "70450", "73700", "72131", "70486", "70480", "72192", "70490", "72128", "71250", "73200"],
        "CT w/": ["74177", "74160", "72126", "70460", "73701", "72132", "70487", "70481", "72193", "70491", "72129", "71260", "73201"],
        "CT w/&w/o": ["74178", "74170", "72127", "70470", "73702", "72133", "70488", "70482", "72194", "70492", "72130", "71270", "73202"],
        "xray": ["74010", "74000", "74020", "76080", "73050", "73600", "73610", "77072", "77073", "73650", "72040", "72050",
                "71010", "71021", "71023", "71022", "71020", "71030", "71034", "71035"]
    }
    
    def __init__(self, db_path: Union[str, Path] = None):
        """
        Initialize the PPO updater.
        
        Args:
            db_path: Path to the SQLite database
        """
        if db_path is None:
            db_path = r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Documents\Bill_Review_INTERNAL\reference_tables\orders2.db"
        
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    def connect_db(self) -> sqlite3.Connection:
        """Create a database connection."""
        return sqlite3.connect(self.db_path)
    
    def update_rate_by_category(self, 
                               state: str, 
                               tin: str, 
                               provider_name: str, 
                               category_rates: Dict[str, float]) -> Tuple[bool, str]:
        """
        Update rates for multiple procedure codes based on their category.
        
        Args:
            state: Rendering state (e.g., TX)
            tin: Provider TIN
            provider_name: Provider name
            category_rates: Dictionary mapping categories to rates
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Clean TIN
            tin = self._clean_tin(tin)
            
            # Prepare data for insertion
            data_rows = []
            for category, rate in category_rates.items():
                if category in self.PROCEDURE_CATEGORIES:
                    proc_codes = self.PROCEDURE_CATEGORIES[category]
                    for proc_cd in proc_codes:
                        # Check if this entry already exists
                        exists = self._check_entry_exists(tin, proc_cd)
                        
                        if exists:
                            # Update existing entry
                            self._update_entry(state, tin, provider_name, proc_cd, "", rate)
                        else:
                            # Add to new entries
                            data_rows.append([
                                state, tin, provider_name, proc_cd, "", 
                                f"Procedure {proc_cd}", category, rate
                            ])
            
            # If we have new entries, insert them
            if data_rows:
                df = pd.DataFrame(
                    data_rows, 
                    columns=["RenderingState", "TIN", "provider_name", "proc_cd", 
                            "modifier", "proc_desc", "proc_category", "rate"]
                )
                
                # Insert into database
                with self.connect_db() as conn:
                    df.to_sql("ppo", con=conn, if_exists='append', index=False)
            
            return True, f"Updated rates for {sum(len(self.PROCEDURE_CATEGORIES[cat]) for cat in category_rates)} procedures"
            
        except Exception as e:
            return False, f"Error updating rates: {str(e)}"
    
    def update_single_rate(self, 
                          state: str, 
                          tin: str, 
                          provider_name: str,
                          proc_cd: str,
                          modifier: str,
                          rate: float) -> Tuple[bool, str]:
        """
        Update a single procedure rate.
        
        Args:
            state: Rendering state (e.g., TX)
            tin: Provider TIN
            provider_name: Provider name
            proc_cd: Procedure code
            modifier: Procedure modifier (can be empty)
            rate: Rate amount
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Clean TIN
            tin = self._clean_tin(tin)
            
            # Check if entry exists
            exists = self._check_entry_exists(tin, proc_cd, modifier)
            
            if exists:
                # Update existing entry
                self._update_entry(state, tin, provider_name, proc_cd, modifier, rate)
            else:
                # Get procedure category
                category = self._get_procedure_category(proc_cd)
                
                # Insert new entry
                with self.connect_db() as conn:
                    query = """
                    INSERT INTO ppo (RenderingState, TIN, provider_name, proc_cd, modifier, proc_desc, proc_category, rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    conn.execute(
                        query, 
                        (state, tin, provider_name, proc_cd, modifier, f"Procedure {proc_cd}", category, rate)
                    )
                    conn.commit()
            
            return True, f"Updated rate for procedure {proc_cd}{' '+modifier if modifier else ''}"
            
        except Exception as e:
            return False, f"Error updating rate: {str(e)}"
    
    def update_rates_from_failures(self, 
                                  failures_df: pd.DataFrame, 
                                  default_rate: float = 500.0,
                                  state: str = "XX") -> Tuple[bool, Dict]:
        """
        Update rates based on validation failures.
        
        Args:
            failures_df: DataFrame containing rate validation failures
            default_rate: Default rate to use if not specified
            state: Default state to use if not in the data
            
        Returns:
            Tuple of (success, report)
        """
        if failures_df.empty:
            return False, {"error": "No failures data provided"}
        
        report = {
            "updated": 0,
            "failed": 0,
            "details": []
        }
        
        for _, failure in failures_df.iterrows():
            try:
                tin = failure.get('provider_tin', '')
                if not tin:
                    tin = failure.get('billing_tin', '')
                
                if not tin:
                    report["failed"] += 1
                    report["details"].append({
                        "status": "failed",
                        "cpt": failure.get('cpt', ''),
                        "reason": "No TIN found"
                    })
                    continue
                
                # Clean TIN
                tin = self._clean_tin(tin)
                if not tin:
                    report["failed"] += 1
                    report["details"].append({
                        "status": "failed",
                        "cpt": failure.get('cpt', ''),
                        "reason": "Invalid TIN format"
                    })
                    continue
                
                # Get CPT code
                cpt = failure.get('cpt', '')
                if not cpt:
                    report["failed"] += 1
                    report["details"].append({
                        "status": "failed",
                        "cpt": "unknown",
                        "reason": "No CPT found"
                    })
                    continue
                
                # Get provider name
                provider_name = failure.get('provider_name', 'Unknown Provider')
                
                # Get modifier
                modifier = failure.get('modifier', '')
                
                # Determine rate based on category
                category = self._get_procedure_category(cpt)
                
                # Update the rate
                success, message = self.update_single_rate(
                    state=state,
                    tin=tin,
                    provider_name=provider_name,
                    proc_cd=cpt,
                    modifier=modifier,
                    rate=default_rate
                )
                
                if success:
                    report["updated"] += 1
                    report["details"].append({
                        "status": "updated",
                        "cpt": cpt,
                        "tin": tin,
                        "provider": provider_name,
                        "rate": default_rate
                    })
                else:
                    report["failed"] += 1
                    report["details"].append({
                        "status": "failed",
                        "cpt": cpt,
                        "reason": message
                    })
                
            except Exception as e:
                report["failed"] += 1
                report["details"].append({
                    "status": "failed",
                    "cpt": failure.get('cpt', 'unknown'),
                    "reason": str(e)
                })
        
        return report["updated"] > 0, report
    
    def get_provider_rates(self, tin: str) -> pd.DataFrame:
        """
        Get existing rates for a provider.
        
        Args:
            tin: Provider TIN
            
        Returns:
            DataFrame of rates
        """
        # Clean TIN
        tin = self._clean_tin(tin)
        
        # Query database
        with self.connect_db() as conn:
            query = "SELECT * FROM ppo WHERE TIN = ?"
            df = pd.read_sql_query(query, conn, params=[tin])
        
        return df
    
    def _check_entry_exists(self, tin: str, proc_cd: str, modifier: str = "") -> bool:
        """Check if an entry already exists in the database."""
        with self.connect_db() as conn:
            query = "SELECT COUNT(*) FROM ppo WHERE TIN = ? AND proc_cd = ? AND modifier = ?"
            cursor = conn.execute(query, (tin, proc_cd, modifier))
            count = cursor.fetchone()[0]
        
        return count > 0
    
    def _update_entry(self, state: str, tin: str, provider_name: str, 
                     proc_cd: str, modifier: str, rate: float) -> None:
        """Update an existing entry in the database."""
        with self.connect_db() as conn:
            query = """
            UPDATE ppo
            SET RenderingState = ?, provider_name = ?, rate = ?
            WHERE TIN = ? AND proc_cd = ? AND modifier = ?
            """
            conn.execute(query, (state, provider_name, rate, tin, proc_cd, modifier))
            conn.commit()
    
    def _get_procedure_category(self, proc_cd: str) -> str:
        """Get the category for a procedure code."""
        for category, codes in self.PROCEDURE_CATEGORIES.items():
            if proc_cd in codes:
                return category
        
        return "Other"
    
    def _clean_tin(self, tin: str) -> str:
        """Clean a TIN string by removing non-numeric characters."""
        if not tin:
            return ""
            
        # Remove non-numeric characters
        clean_tin = ''.join(c for c in str(tin) if c.isdigit())
        
        # Ensure it's 9 digits
        if len(clean_tin) == 9:
            return clean_tin
            
        return ""
    
    @classmethod
    def get_all_categories(cls) -> List[str]:
        """Get a list of all procedure categories."""
        return list(cls.PROCEDURE_CATEGORIES.keys())
    
    @classmethod
    def get_procedures_in_category(cls, category: str) -> List[str]:
        """Get a list of procedure codes in a category."""
        return cls.PROCEDURE_CATEGORIES.get(category, [])