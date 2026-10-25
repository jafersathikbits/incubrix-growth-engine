import pytest
from src.database import init_db, is_duplicate, insert_lead, generate_lead_id

def test_deduplication(tmp_path):
    # Use a temporary database for testing
    db_path = tmp_path / "test.db"
    init_db(db_path)
    
    channel_id = "UC123456789"
    
    # 1. Should not be a duplicate initially
    assert is_duplicate(db_path, channel_id) == False
    
    # 2. Insert a lead
    lead_data = {
        'stable_creator_id': channel_id,
        'creator_name': "Test Creator",
        'candidate_status': 'Qualified'
    }
    insert_lead(db_path, lead_data)
    
    # 3. Now it should be detected as a duplicate
    assert is_duplicate(db_path, channel_id) == True

def test_hashing():
    channel_id = "UC123456789"
    hash1 = generate_lead_id(channel_id)
    hash2 = generate_lead_id(channel_id)
    assert hash1 == hash2
    assert len(hash1) == 64 # SHA-256 length