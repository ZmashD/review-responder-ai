import json
import random
import time
import os

# Configuration path pointing to your config directory
MOCK_DATA_PATH = os.path.join("config", "mock_reviews_pool.json")

def load_reviews_pool():
    """
    Safely opens and loads the array of reviews from the configuration folder.
    """
    if not os.path.exists(MOCK_DATA_PATH):
        print(f"Error: Could not find mock data file at {MOCK_DATA_PATH}")
        return []
    
    try:
        with open(MOCK_DATA_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error parsing JSON data: {str(e)}")
        return []

def fetch_next_simulated_review(exclude_ids=None):
    """
    Selects a random review from the pool.
    Allows optional exclusion of IDs to prevent immediate repeats during a live session.
    """
    pool = load_reviews_pool()
    if not pool:
        return None
        
    if exclude_ids:
        # Filter down the pool to elements we haven't seen immediately
        available_pool = [r for r in pool if r.get("review_id") not in exclude_ids]
        # Fallback if we exhausted the list
        if not available_pool:
            available_pool = pool
    else:
        available_pool = pool

    return random.choice(available_pool)

# Small isolated test block to verify operation if run standalone
if __name__ == "__main__":
    print("🔄 Running quick standalone validation check on Ingestion Engine...")
    test_review = fetch_next_simulated_review()
    if test_review:
        print("\n✅ Successfully retrieved data stream specimen:")
        print(f"ID: {test_review['review_id']}")
        print(f"Author: {test_review['customer_name']}")
        print(f"Platform: {test_review['source_platform']}")
        print(f"Content: '{test_review['review_text']}'\n")
    else:
        print("❌ Test failed. Verify file location configuration.")