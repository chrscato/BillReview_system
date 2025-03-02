# core/services/database.py
import sqlite3
import pandas as pd
from typing import Dict, Optional
from config.settings import settings

class DatabaseService:
    @staticmethod
    def connect_db():
        """Create database connection"""
        return sqlite3.connect(settings.DB_PATH)

    @staticmethod
    def get_line_items(order_id: str, conn: sqlite3.Connection) -> pd.DataFrame:
        """Get line items for an order"""
        query = """
        SELECT id, Order_ID, DOS, CPT, Modifier, Units, Description
        FROM line_items
        WHERE Order_ID = ?
        """
        return pd.read_sql_query(query, conn, params=[order_id])

    @staticmethod
    def get_provider_details(order_id: str, conn: sqlite3.Connection) -> Optional[Dict]:
        """Get provider details through the orders-providers relationship."""
        query = """
        SELECT 
            p."Address 1 Full",
            p."Billing Address 1",
            p."Billing Address 2",
            p."Billing Address City",
            p."Billing Address Postal Code",
            p."Billing Address State",
            p."Billing Name",
            p."DBA Name Billing Name",
            p."Latitude",
            p."Location",
            p."Need OTA",
            p."Provider Network",
            p."Provider Status",
            p."Provider Type",
            p."TIN",
            p."NPI",
            p.PrimaryKey
        FROM orders o
        JOIN providers p ON o.provider_id = p.PrimaryKey
        WHERE o.Order_ID = ?
        """
        
        df = pd.read_sql_query(query, conn, params=[order_id])
        if df.empty:
            return None
        return df.iloc[0].to_dict()

    @staticmethod
    def get_full_details(order_id: str, conn: sqlite3.Connection) -> Dict:
        """Fetch all related data for an order"""
        queries = {
            "order_details": "SELECT * FROM orders WHERE Order_ID = ?",
            "provider_details": """
            SELECT p.* 
            FROM orders o
            JOIN providers p ON o.provider_id = p.PrimaryKey
            WHERE o.Order_ID = ?
            """,
            "line_items": "SELECT * FROM line_items WHERE Order_ID = ?"
        }
        
        results = {}
        for table_name, query in queries.items():
            df = pd.read_sql_query(query, conn, params=[order_id])
            if not df.empty:
                results[table_name] = df.iloc[0].to_dict()
                
        return results

    @staticmethod
    def check_bundle(order_id: str, conn: sqlite3.Connection) -> bool:
        """Check if order is bundled"""
        query = "SELECT bundle_type FROM orders WHERE Order_ID = ?"
        result = pd.read_sql_query(query, conn, params=[order_id])
        if result.empty:
            return False
        return pd.notna(result['bundle_type'].iloc[0])