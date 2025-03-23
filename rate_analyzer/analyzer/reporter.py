"""
Reporter module for generating reports on rate validation failures.
"""
import pandas as pd
import json
from pathlib import Path
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Union, Any
import os
import datetime

class ReportGenerator:
    """Generator for rate validation failure reports."""
    
    def __init__(self, failures_df: Optional[pd.DataFrame] = None, summary: Optional[Dict] = None):
        """
        Initialize the report generator.
        
        Args:
            failures_df: DataFrame containing rate validation failures
            summary: Summary statistics from the aggregator
        """
        self.failures_df = failures_df
        self.summary = summary
        self.output_dir = None
    
    def set_data(self, failures_df: pd.DataFrame, summary: Dict):
        """
        Set data for report generation.
        
        Args:
            failures_df: DataFrame containing rate validation failures
            summary: Summary statistics from the aggregator
        """
        self.failures_df = failures_df
        self.summary = summary
    
    def set_output_directory(self, output_dir: Union[str, Path]):
        """
        Set the output directory for reports.
        
        Args:
            output_dir: Directory path for saving reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_all_reports(self, timestamp: Optional[str] = None) -> Dict[str, Path]:
        """
        Generate all available reports.
        
        Args:
            timestamp: Optional timestamp to include in filenames
            
        Returns:
            Dict[str, Path]: Dictionary of report types and their file paths
        """
        if self.failures_df is None or self.failures_df.empty:
            return {"error": "No data available for reports"}
        
        if self.output_dir is None:
            raise ValueError("Output directory not set. Call set_output_directory() first.")
        
        # Create timestamp if not provided
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate reports
        report_paths = {}
        
        # Excel report
        excel_path = self.generate_excel_report(timestamp)
        if excel_path:
            report_paths["excel"] = excel_path
        
        # JSON summary
        json_path = self.generate_json_summary(timestamp)
        if json_path:
            report_paths["json"] = json_path
        
        # Charts
        charts_dir = self.generate_charts(timestamp)
        if charts_dir:
            report_paths["charts"] = charts_dir
        
        return report_paths
    
    def generate_excel_report(self, timestamp: Optional[str] = None) -> Optional[Path]:
        """
        Generate an Excel report with multiple sheets for different analyses.
        
        Args:
            timestamp: Optional timestamp to include in the filename
            
        Returns:
            Optional[Path]: Path to the generated Excel file
        """
        if self.failures_df is None or self.failures_df.empty:
            return None
        
        if self.output_dir is None:
            raise ValueError("Output directory not set. Call set_output_directory() first.")
        
        # Create timestamp if not provided
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create Excel writer
        excel_path = self.output_dir / f"rate_validation_report_{timestamp}.xlsx"
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Sheet 1: Overview
            self._create_overview_sheet(writer)
            
            # Sheet 2: Provider Analysis
            self._create_provider_sheet(writer)
            
            # Sheet 3: CPT Analysis
            self._create_cpt_sheet(writer)
            
            # Sheet 4: Detailed Failures
            self.failures_df.to_excel(writer, sheet_name='Detailed Failures', index=False)
            
            # Sheet 5: High Priority Issues
            self._create_priority_sheet(writer)
        
        return excel_path
    
    def _create_overview_sheet(self, writer):
        """Create overview sheet in Excel report."""
        if not self.summary:
            return
        
        # Create overview data
        overview_data = {
            'Metric': [
                'Total Failures',
                'Unique Providers',
                'Unique CPT Codes',
                'Total Charge Amount',
                'Average Charge per Failure'
            ],
            'Value': [
                self.summary.get('total_failures', 0),
                self.summary.get('unique_providers', {}).get('count', 0),
                self.summary.get('cpt_analysis', {}).get('count', 0),
                f"${self.summary.get('financial_impact', {}).get('total_charge', 0):,.2f}",
                f"${self.summary.get('financial_impact', {}).get('average_charge', 0):,.2f}"
            ]
        }
        
        # Create DataFrame and write to Excel
        overview_df = pd.DataFrame(overview_data)
        overview_df.to_excel(writer, sheet_name='Overview', index=False)
        
        # Network status data
        network_data = self.summary.get('network_status', {})
        if network_data and 'counts' in network_data:
            network_df = pd.DataFrame({
                'Network Status': list(network_data['counts'].keys()),
                'Count': list(network_data['counts'].values()),
                'Percentage': [f"{p:.1f}%" for p in network_data['percentages'].values()],
                'Total Charge': [f"${c:,.2f}" for c in network_data['charges'].values()]
            })
            
            # Write to Excel starting from row 8
            network_df.to_excel(writer, sheet_name='Overview', startrow=7, index=False)
    
    def _create_provider_sheet(self, writer):
        """Create provider analysis sheet in Excel report."""
        if not self.summary or 'unique_providers' not in self.summary:
            return
        
        # Extract provider data
        providers = self.summary['unique_providers'].get('providers', {})
        
        # Create provider DataFrame
        provider_data = []
        for tin, info in providers.items():
            provider_data.append({
                'TIN': tin,
                'Provider Name': info.get('name', 'Unknown'),
                'Failure Count': info.get('failure_count', 0),
                'Total Charge': info.get('total_charge', 0)
            })
        
        provider_df = pd.DataFrame(provider_data)
        
        # Sort by failure count (descending)
        provider_df = provider_df.sort_values('Failure Count', ascending=False)
        
        # Format total charge as currency
        provider_df['Total Charge'] = provider_df['Total Charge'].apply(lambda x: f"${x:,.2f}")
        
        # Write to Excel
        provider_df.to_excel(writer, sheet_name='Provider Analysis', index=False)
    
    def _create_cpt_sheet(self, writer):
        """Create CPT analysis sheet in Excel report."""
        if not self.summary or 'cpt_analysis' not in self.summary:
            return
        
        # Extract CPT data
        cpt_codes = self.summary['cpt_analysis'].get('cpt_codes', {})
        
        # Create CPT DataFrame
        cpt_data = []
        for cpt, info in cpt_codes.items():
            cpt_data.append({
                'CPT Code': cpt,
                'Failure Count': info.get('failure_count', 0),
                'Total Charge': info.get('total_charge', 0),
                'Provider Count': info.get('provider_count', 0)
            })
        
        cpt_df = pd.DataFrame(cpt_data)
        
        # Sort by failure count (descending)
        cpt_df = cpt_df.sort_values('Failure Count', ascending=False)
        
        # Format total charge as currency
        cpt_df['Total Charge'] = cpt_df['Total Charge'].apply(lambda x: f"${x:,.2f}")
        
        # Write to Excel
        cpt_df.to_excel(writer, sheet_name='CPT Analysis', index=False)
        
        # Add CPT-TIN combinations
        cpt_tin_combos = self.summary['cpt_analysis'].get('top_cpt_tin_combinations', [])
        if cpt_tin_combos:
            combo_df = pd.DataFrame(cpt_tin_combos)
            combo_df.columns = ['CPT Code', 'TIN', 'Provider Name', 'Failure Count']
            combo_df.to_excel(writer, sheet_name='CPT Analysis', startrow=len(cpt_df) + 3, index=False)
    
    def _create_priority_sheet(self, writer):
        """Create high priority issues sheet in Excel report."""
        if not self.summary or 'high_priority_issues' not in self.summary:
            return
        
        # Extract priority issues
        priority_issues = self.summary.get('high_priority_issues', [])
        
        # Create priority DataFrame
        priority_df = pd.DataFrame(priority_issues)
        
        # Format columns
        if not priority_df.empty:
            priority_df['total_charge'] = priority_df['total_charge'].apply(lambda x: f"${x:,.2f}")
            priority_df['priority_score'] = priority_df['priority_score'].apply(lambda x: f"{x:.1f}")
            
            # Rename columns
            priority_df.columns = [
                'CPT Code', 'TIN', 'Provider Name', 'Failure Count', 
                'Total Charge', 'Priority Score'
            ]
        
        # Write to Excel
        priority_df.to_excel(writer, sheet_name='High Priority Issues', index=False)
    
    def generate_json_summary(self, timestamp: Optional[str] = None) -> Optional[Path]:
        """
        Generate a JSON summary of rate validation failures.
        
        Args:
            timestamp: Optional timestamp to include in the filename
            
        Returns:
            Optional[Path]: Path to the generated JSON file
        """
        if not self.summary:
            return None
        
        if self.output_dir is None:
            raise ValueError("Output directory not set. Call set_output_directory() first.")
        
        # Create timestamp if not provided
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create JSON file path
        json_path = self.output_dir / f"rate_validation_summary_{timestamp}.json"
        
        # Write summary to JSON file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.summary, f, indent=2)
        
        return json_path
    
    def generate_charts(self, timestamp: Optional[str] = None) -> Optional[Path]:
        """
        Generate charts visualizing rate validation failures.
        
        Args:
            timestamp: Optional timestamp to include in filenames
            
        Returns:
            Optional[Path]: Path to the directory containing generated charts
        """
        if self.failures_df is None or self.failures_df.empty or not self.summary:
            return None
        
        if self.output_dir is None:
            raise ValueError("Output directory not set. Call set_output_directory() first.")
        
        # Create timestamp if not provided
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create charts directory
        charts_dir = self.output_dir / f"charts_{timestamp}"
        charts_dir.mkdir(exist_ok=True)
        
        # Generate charts
        self._generate_provider_chart(charts_dir)
        self._generate_cpt_chart(charts_dir)
        self._generate_network_chart(charts_dir)
        self._generate_priority_chart(charts_dir)
        
        return charts_dir
    
    def _generate_provider_chart(self, charts_dir: Path):
        """Generate provider analysis chart."""
        if not self.summary or 'unique_providers' not in self.summary:
            return
        
        # Extract top 10 providers by failure count
        providers = self.summary['unique_providers'].get('providers', {})
        
        # Create data for chart
        top_providers = []
        for tin, info in providers.items():
            top_providers.append({
                'tin': tin,
                'name': info.get('name', 'Unknown'),
                'count': info.get('failure_count', 0)
            })
        
        # Sort by count (descending) and take top 10
        top_providers.sort(key=lambda x: x['count'], reverse=True)
        top_providers = top_providers[:10]
        
        # Create bar chart
        plt.figure(figsize=(12, 8))
        
        names = [f"{p['name'][:20]}... ({p['tin']})" if len(p['name']) > 20 
                else f"{p['name']} ({p['tin']})" for p in top_providers]
        counts = [p['count'] for p in top_providers]
        
        plt.barh(names, counts, color='skyblue')
        plt.xlabel('Failure Count')
        plt.ylabel('Provider (TIN)')
        plt.title('Top 10 Providers by Rate Validation Failures')
        plt.tight_layout()
        
        # Save chart
        plt.savefig(charts_dir / 'top_providers.png', dpi=300)
        plt.close()
    
    def _generate_cpt_chart(self, charts_dir: Path):
        """Generate CPT analysis chart."""
        if not self.summary or 'cpt_analysis' not in self.summary:
            return
        
        # Extract top 10 CPT codes by failure count
        cpt_codes = self.summary['cpt_analysis'].get('cpt_codes', {})
        
        # Create data for chart
        top_cpts = []
        for cpt, info in cpt_codes.items():
            top_cpts.append({
                'cpt': cpt,
                'count': info.get('failure_count', 0)
            })
        
        # Sort by count (descending) and take top 10
        top_cpts.sort(key=lambda x: x['count'], reverse=True)
        top_cpts = top_cpts[:10]
        
        # Create bar chart
        plt.figure(figsize=(12, 8))
        
        cpts = [p['cpt'] for p in top_cpts]
        counts = [p['count'] for p in top_cpts]
        
        plt.barh(cpts, counts, color='lightgreen')
        plt.xlabel('Failure Count')
        plt.ylabel('CPT Code')
        plt.title('Top 10 CPT Codes by Rate Validation Failures')
        plt.tight_layout()
        
        # Save chart
        plt.savefig(charts_dir / 'top_cpts.png', dpi=300)
        plt.close()
    
    def _generate_network_chart(self, charts_dir: Path):
        """Generate network status chart."""
        if not self.summary or 'network_status' not in self.summary:
            return
        
        # Extract network status data
        network_data = self.summary['network_status'].get('counts', {})
        
        if not network_data:
            return
        
        # Create pie chart
        plt.figure(figsize=(10, 10))
        
        labels = list(network_data.keys())
        sizes = list(network_data.values())
        
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, shadow=True)
        plt.axis('equal')
        plt.title('Rate Validation Failures by Network Status')
        
        # Save chart
        plt.savefig(charts_dir / 'network_status.png', dpi=300)
        plt.close()
    
    def _generate_priority_chart(self, charts_dir: Path):
        """Generate high priority issues chart."""
        if not self.summary or 'high_priority_issues' not in self.summary:
            return
        
        # Extract priority issues
        priority_issues = self.summary.get('high_priority_issues', [])
        
        if not priority_issues:
            return
        
        # Create data for chart
        labels = [f"{p['cpt']} - {p['provider_name'][:15]}..." if len(p['provider_name']) > 15 
                 else f"{p['cpt']} - {p['provider_name']}" for p in priority_issues[:8]]
        scores = [p['priority_score'] for p in priority_issues[:8]]
        
        # Create bar chart
        plt.figure(figsize=(12, 8))
        
        plt.barh(labels, scores, color='salmon')
        plt.xlabel('Priority Score')
        plt.ylabel('CPT - Provider')
        plt.title('High Priority Rate Validation Issues')
        plt.tight_layout()
        
        # Save chart
        plt.savefig(charts_dir / 'priority_issues.png', dpi=300)
        plt.close()
    
    def to_sqlite(self, db_path: Union[str, Path]) -> bool:
        """
        Export rate validation failures to SQLite database.
        
        Args:
            db_path: Path to SQLite database file
            
        Returns:
            bool: True if export was successful, False otherwise
        """
        if self.failures_df is None or self.failures_df.empty:
            return False
        
        try:
            import sqlite3
            
            # Connect to database
            conn = sqlite3.connect(str(db_path))
            
            # Create tables if they don't exist
            conn.execute('''
            CREATE TABLE IF NOT EXISTS rate_failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                order_id TEXT,
                patient_name TEXT,
                date_of_service TEXT,
                provider_name TEXT,
                provider_tin TEXT,
                provider_npi TEXT,
                provider_network TEXT,
                billing_tin TEXT,
                total_charge REAL,
                cpt TEXT,
                modifier TEXT,
                units INTEGER,
                charge REAL,
                error_code TEXT,
                error_message TEXT,
                timestamp TEXT
            )
            ''')
            
            # Export data to database
            self.failures_df.to_sql('rate_failures', conn, if_exists='append', index=False)
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error exporting to SQLite: {str(e)}")
            return False