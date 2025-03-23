"""
Aggregator module for analyzing and grouping rate validation failures.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter

class RateFailureAggregator:
    """Aggregator for analyzing rate validation failures."""
    
    def __init__(self, failures_df: Optional[pd.DataFrame] = None):
        """
        Initialize the aggregator with optional failures DataFrame.
        
        Args:
            failures_df: DataFrame containing rate validation failures
        """
        self.failures_df = failures_df
        self.summary = {}
    
    def set_data(self, failures_df: pd.DataFrame):
        """
        Set the failures data for analysis.
        
        Args:
            failures_df: DataFrame containing rate validation failures
        """
        self.failures_df = failures_df
    
    def analyze(self) -> Dict:
        """
        Analyze rate validation failures and generate summary statistics.
        
        Returns:
            Dict: Summary statistics and insights
        """
        if self.failures_df is None or self.failures_df.empty:
            return {"error": "No data available for analysis"}
        
        # Clean and prepare data
        self._prepare_data()
        
        # Generate summary
        self.summary = {
            "total_failures": len(self.failures_df),
            "unique_providers": self._analyze_providers(),
            "cpt_analysis": self._analyze_cpt_codes(),
            "financial_impact": self._analyze_financial_impact(),
            "network_status": self._analyze_network_status(),
            "high_priority_issues": self._identify_high_priority_issues()
        }
        
        return self.summary
    
    def _prepare_data(self):
        """Clean and prepare data for analysis."""
        # Convert numeric columns
        numeric_columns = ['units', 'charge']
        for col in numeric_columns:
            if col in self.failures_df.columns:
                self.failures_df[col] = pd.to_numeric(self.failures_df[col], errors='coerce')
        
        # Fill missing values
        self.failures_df = self.failures_df.fillna({
            'units': 1,
            'charge': 0.0,
            'provider_network': 'Unknown'
        })
        
        # Create a charge_total column (charge × units)
        if 'units' in self.failures_df.columns and 'charge' in self.failures_df.columns:
            self.failures_df['charge_total'] = self.failures_df['charge'] * self.failures_df['units']
    
    def _analyze_providers(self) -> Dict:
        """
        Analyze providers (TINs) with rate failures.
        
        Returns:
            Dict: Provider analysis results
        """
        if 'provider_tin' not in self.failures_df.columns:
            return {}
        
        # Count failures by provider
        provider_counts = self.failures_df['provider_tin'].value_counts().to_dict()
        
        # Get total charge by provider
        provider_charges = self.failures_df.groupby('provider_tin')['charge_total'].sum().to_dict()
        
        # Combine provider data with names
        providers_data = {}
        for tin, count in provider_counts.items():
            # Get a sample provider name for this TIN
            provider_name = self.failures_df[self.failures_df['provider_tin'] == tin]['provider_name'].iloc[0] \
                if not self.failures_df[self.failures_df['provider_tin'] == tin]['provider_name'].empty else 'Unknown'
            
            providers_data[tin] = {
                'name': provider_name,
                'failure_count': count,
                'total_charge': provider_charges.get(tin, 0)
            }
        
        # Sort providers by failure count (descending)
        sorted_providers = {
            k: v for k, v in sorted(
                providers_data.items(), 
                key=lambda item: item[1]['failure_count'], 
                reverse=True
            )
        }
        
        return {
            'count': len(sorted_providers),
            'providers': sorted_providers,
            'top_providers': list(sorted_providers.keys())[:5]
        }
    
    def _analyze_cpt_codes(self) -> Dict:
        """
        Analyze CPT codes with rate failures.
        
        Returns:
            Dict: CPT code analysis results
        """
        if 'cpt' not in self.failures_df.columns:
            return {}
        
        # Count failures by CPT
        cpt_counts = self.failures_df['cpt'].value_counts().to_dict()
        
        # Get total charge by CPT
        cpt_charges = self.failures_df.groupby('cpt')['charge_total'].sum().to_dict()
        
        # Get providers using each CPT
        cpt_providers = {}
        for cpt in cpt_counts.keys():
            providers = self.failures_df[self.failures_df['cpt'] == cpt]['provider_tin'].unique().tolist()
            cpt_providers[cpt] = providers
        
        # Combine CPT data
        cpt_data = {}
        for cpt, count in cpt_counts.items():
            cpt_data[cpt] = {
                'failure_count': count,
                'total_charge': cpt_charges.get(cpt, 0),
                'providers': cpt_providers.get(cpt, []),
                'provider_count': len(cpt_providers.get(cpt, []))
            }
        
        # Sort CPTs by failure count (descending)
        sorted_cpts = {
            k: v for k, v in sorted(
                cpt_data.items(), 
                key=lambda item: item[1]['failure_count'], 
                reverse=True
            )
        }
        
        # CPT-TIN combinations (which CPTs fail with which providers)
        cpt_tin_combinations = self.failures_df.groupby(['cpt', 'provider_tin']).size().reset_index(name='count')
        top_combinations = cpt_tin_combinations.sort_values('count', ascending=False).head(10)
        
        # Convert top combinations to dictionary
        top_cpt_tin = []
        for _, row in top_combinations.iterrows():
            cpt = row['cpt']
            tin = row['provider_tin']
            count = row['count']
            
            # Get provider name
            provider_name = self.failures_df[
                (self.failures_df['cpt'] == cpt) & 
                (self.failures_df['provider_tin'] == tin)
            ]['provider_name'].iloc[0] if not self.failures_df[
                (self.failures_df['cpt'] == cpt) & 
                (self.failures_df['provider_tin'] == tin)
            ]['provider_name'].empty else 'Unknown'
            
            top_cpt_tin.append({
                'cpt': cpt,
                'tin': tin,
                'provider_name': provider_name,
                'count': count
            })
        
        return {
            'count': len(sorted_cpts),
            'cpt_codes': sorted_cpts,
            'top_cpt_codes': list(sorted_cpts.keys())[:10],
            'top_cpt_tin_combinations': top_cpt_tin
        }
    
    def _analyze_financial_impact(self) -> Dict:
        """
        Analyze financial impact of rate failures.
        
        Returns:
            Dict: Financial impact analysis results
        """
        if 'charge_total' not in self.failures_df.columns:
            return {}
        
        # Total charge amount
        total_charge = self.failures_df['charge_total'].sum()
        
        # Average charge per failure
        avg_charge = self.failures_df['charge_total'].mean()
        
        # Distribution of charges
        charge_distribution = {
            'min': self.failures_df['charge_total'].min(),
            'max': self.failures_df['charge_total'].max(),
            'median': self.failures_df['charge_total'].median(),
            'q1': self.failures_df['charge_total'].quantile(0.25),
            'q3': self.failures_df['charge_total'].quantile(0.75)
        }
        
        return {
            'total_charge': total_charge,
            'average_charge': avg_charge,
            'charge_distribution': charge_distribution
        }
    
    def _analyze_network_status(self) -> Dict:
        """
        Analyze network status of providers with rate failures.
        
        Returns:
            Dict: Network status analysis results
        """
        if 'provider_network' not in self.failures_df.columns:
            return {}
        
        # Count failures by network status
        network_counts = self.failures_df['provider_network'].value_counts().to_dict()
        
        # Calculate percentage by network status
        total = sum(network_counts.values())
        network_percentages = {k: (v / total) * 100 for k, v in network_counts.items()}
        
        # Get total charge by network status
        network_charges = self.failures_df.groupby('provider_network')['charge_total'].sum().to_dict()
        
        return {
            'counts': network_counts,
            'percentages': network_percentages,
            'charges': network_charges
        }
    
    def _identify_high_priority_issues(self) -> List[Dict]:
        """
        Identify high-priority issues based on frequency and financial impact.
        
        Returns:
            List[Dict]: High-priority issues
        """
        if self.failures_df.empty:
            return []
        
        # Calculate a priority score
        # Priority = (frequency_score * 0.6) + (financial_impact_score * 0.4)
        
        # Get top CPT-TIN combinations
        cpt_tin_groups = self.failures_df.groupby(['cpt', 'provider_tin'])
        
        priority_issues = []
        for (cpt, tin), group in cpt_tin_groups:
            frequency = len(group)
            total_charge = group['charge_total'].sum()
            
            # Get max frequency and charge for normalization
            max_frequency = self.failures_df.groupby(['cpt', 'provider_tin']).size().max()
            max_charge = self.failures_df.groupby(['cpt', 'provider_tin'])['charge_total'].sum().max()
            
            # Normalize scores (0-100)
            frequency_score = (frequency / max_frequency) * 100 if max_frequency > 0 else 0
            financial_score = (total_charge / max_charge) * 100 if max_charge > 0 else 0
            
            # Calculate priority score
            priority_score = (frequency_score * 0.6) + (financial_score * 0.4)
            
            # Get provider name
            provider_name = group['provider_name'].iloc[0] if not group['provider_name'].empty else 'Unknown'
            
            priority_issues.append({
                'cpt': cpt,
                'provider_tin': tin,
                'provider_name': provider_name,
                'frequency': frequency,
                'total_charge': total_charge,
                'priority_score': priority_score
            })
        
        # Sort by priority score (descending)
        priority_issues.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Return top 10 issues
        return priority_issues[:10]
    
    def get_provider_cpt_matrix(self) -> pd.DataFrame:
        """
        Generate a matrix of providers (TINs) vs CPT codes.
        
        Returns:
            pd.DataFrame: Provider-CPT matrix with failure counts
        """
        if self.failures_df is None or self.failures_df.empty:
            return pd.DataFrame()
        
        # Create a pivot table of provider TINs vs CPT codes
        if 'provider_tin' in self.failures_df.columns and 'cpt' in self.failures_df.columns:
            pivot = pd.pivot_table(
                self.failures_df,
                values='charge_total',
                index='provider_tin',
                columns='cpt',
                aggfunc='sum',
                fill_value=0
            )
            
            return pivot
        
        return pd.DataFrame()