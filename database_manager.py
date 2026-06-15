import os
import sqlite3
from datetime import datetime

# Define global path configurations
DB_DIR = "data"
DB_NAME = "reputation_management.db"
DB_PATH = os.path.join(DB_DIR, DB_NAME)

def init_db():
    """
    Initializes the local SQLite database environment. Creates the target 
    storage directory and establishes the analytics table schema if not present.
    """
    # Create the data directory safely if it doesn't exist
    os.makedirs(DB_DIR, exist_ok=True)
    
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    
    # Construct the primary analytics tracking ledger
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            brand_profile TEXT NOT NULL,
            review_text TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            escalation_required INTEGER NOT NULL, -- 0 for False, 1 for True
            escalation_reason TEXT,
            draft_response TEXT NOT NULL,
            final_response TEXT NOT NULL,
            was_edited INTEGER NOT NULL          -- 0 for False, 1 for True
        )
    """)
    
    connection.commit()
    connection.close()

def log_review_transaction(
    brand_profile: str,
    review_text: str,
    sentiment: str,
    escalation_required: bool,
    escalation_reason: str,
    draft_response: str,
    final_response: str
) -> bool:
    """
    Commits a completely processed review interaction block into the relational 
    database tracking ledger, computing edit evaluation flags automatically.
    """
    try:
        # Calculate derived analytical dimensions
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_escalated_int = 1 if escalation_required else 0
        
        # Clean white space discrepancies before evaluation comparison
        was_edited_int = 1 if draft_response.strip() != final_response.strip() else 0
        
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        
        # Parameterized insertion block to maintain pipeline security integrity
        query = """
            INSERT INTO review_logs (
                timestamp, brand_profile, review_text, sentiment, 
                escalation_required, escalation_reason, draft_response, 
                final_response, was_edited
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(query, (
            current_time,
            brand_profile,
            review_text.strip(),
            sentiment,
            is_escalated_int,
            escalation_reason.strip() if escalation_reason else "",
            draft_response.strip(),
            final_response.strip(),
            was_edited_int
        ))
        
        connection.commit()
        connection.close()
        return True
        
    except Exception as e:
        # Ensure errors are isolated or print visibility for local debug
        print(f"Database insertion transaction failure: {e}")
        return False