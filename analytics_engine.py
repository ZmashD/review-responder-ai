import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join("data", "reputation_management.db")

def get_db_connection():
    """Helper to establish a read-only connection to the database."""
    return sqlite3.connect(DB_PATH)

def get_overall_kpis():
    """Returns a dictionary of high-level performance metrics."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM review_logs", conn)
    conn.close()
    
    if df.empty:
        return {"total": 0, "escalation_rate": 0, "edit_rate": 0}
        
    total = len(df)
    escalation_rate = (df['escalation_required'].sum() / total) * 100
    edit_rate = (df['was_edited'].sum() / total) * 100
    
    return {
        "total": total,
        "escalation_rate": round(escalation_rate, 1),
        "edit_rate": round(edit_rate, 1)
    }

def get_sentiment_distribution():
    """Returns a DataFrame of review counts grouped by sentiment."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT sentiment, COUNT(*) as count FROM review_logs GROUP BY sentiment", conn)
    conn.close()
    return df

def get_escalation_reasons():
    """Returns a DataFrame of escalation triggers and their frequencies."""
    conn = get_db_connection()
    # Filter only where escalation occurred and reason is not empty
    query = """
    SELECT escalation_reason, COUNT(*) as count 
    FROM review_logs 
    WHERE escalation_required = 1 AND escalation_reason != ''
    GROUP BY escalation_reason
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_brand_performance():
    """Aggregates metrics by brand profile."""
    conn = get_db_connection()
    query = """
    SELECT 
        brand_profile, 
        COUNT(*) as total_reviews,
        AVG(escalation_required) * 100 as escalation_pct,
        AVG(was_edited) * 100 as edit_pct
    FROM review_logs
    GROUP BY brand_profile
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df