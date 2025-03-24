import os
import json
import time
import tempfile
import streamlit as st

# File-based temporary storage for credentials
# This persists across Streamlit restarts unlike in-memory dictionary
TEMP_DIR = tempfile.gettempdir()
TEMP_STORAGE_FILE = os.path.join(TEMP_DIR, "strava_uploader_temp_credentials.json")

# Load existing temp storage if it exists
def load_temp_storage():
    try:
        if os.path.exists(TEMP_STORAGE_FILE):
            with open(TEMP_STORAGE_FILE, 'r') as f:
                data = json.load(f)
                # Clean up expired entries
                current_time = time.time()
                cleaned_data = {k: v for k, v in data.items() 
                               if v.get('expires_at', 0) > current_time}
                # Save cleaned data
                if len(cleaned_data) != len(data):
                    save_temp_storage(cleaned_data)
                return cleaned_data
    except Exception as e:
        if st.session_state.get('debug_mode', False):
            st.error(f"Error loading temp storage: {str(e)}")
    return {}

# Save temp storage
def save_temp_storage(data):
    try:
        with open(TEMP_STORAGE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        if st.session_state.get('debug_mode', False):
            st.error(f"Error saving temp storage: {str(e)}")

# Clean up temp storage entries
def clean_temp_storage():
    temp_storage = load_temp_storage()
    # Clean any old entries
    current_time = time.time()
    cleaned_storage = {k: v for k, v in temp_storage.items() 
                      if v.get('expires_at', 0) > current_time}
    if len(cleaned_storage) != len(temp_storage):
        save_temp_storage(cleaned_storage)
    return cleaned_storage