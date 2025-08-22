from uuid import uuid4 as uuid
from constants import OUTPUT_DIR
import os
from datetime import datetime, timezone
from .time_utils import get_current_pst_time # Import PST utility

def get_output_dir(filename: str) -> str:
    """Get the full path for a file in the current PST date's directory."""
    # Use current PST date for directory structure
    pst_now = get_current_pst_time()
    if not pst_now:
        # Fallback to UTC or raise error if PST is critical
        pst_now = datetime.now(timezone.utc) 
        print("Warning: Could not get PST time, using UTC for directory path.")
    current_pst_date_str = pst_now.strftime('%Y-%m-%d')
    
    description_dir = os.path.join(OUTPUT_DIR, current_pst_date_str)
    os.makedirs(description_dir, exist_ok=True)
    file_path = os.path.join(description_dir, filename)
    return file_path


def get_description_dir() -> str:
    """Get the current PST date's directory path."""
    # Use current PST date for directory structure
    pst_now = get_current_pst_time()
    if not pst_now:
        # Fallback to UTC or raise error if PST is critical
        pst_now = datetime.now(timezone.utc) 
        print("Warning: Could not get PST time, using UTC for description directory path.")
    current_pst_date_str = pst_now.strftime('%Y-%m-%d')
    description_dir = os.path.join(OUTPUT_DIR, current_pst_date_str)
    return description_dir

def generate_id() -> str:
    """Generate a unique ID for a document."""
    return str(uuid())


# Utility function to get current timestamp in ISO format
def get_timestamp() -> str:
    """Get the current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()