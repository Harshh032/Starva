import uuid
import time
import streamlit as st
from utils.storage import load_temp_storage, save_temp_storage

# Save credentials and store in temp_storage
def save_credentials():
    if not st.session_state.client_id_input:
        st.error("Please enter a Client ID.")
        return
    if not st.session_state.client_secret_input:
        st.error("Please enter a Client Secret.")
        return
    try:
        int(st.session_state.client_id_input)
    except ValueError:
        st.error("Client ID must be a number.")
        return
    
    st.session_state.client_id = st.session_state.client_id_input
    st.session_state.client_secret = st.session_state.client_secret_input
    
    # Generate a unique key and store credentials in temp_storage
    temp_key = str(uuid.uuid4())  # Unique identifier
    expiry_time = time.time() + 300  # 5 minutes expiry
    
    # Load latest temp_storage
    temp_storage = load_temp_storage()
    temp_storage[temp_key] = {
        'client_id': st.session_state.client_id,
        'client_secret': st.session_state.client_secret,
        'expires_at': expiry_time
    }
    save_temp_storage(temp_storage)
    
    st.session_state.temp_key = temp_key
    
    # Change phase to authorization
    st.session_state.phase = 'authorization'

# Retrieve credentials (from session_state or temp_storage)
def get_credentials():
    client_id = st.session_state.client_id
    client_secret = st.session_state.client_secret
    
    # If credentials are missing in session_state, check temp_storage
    if not client_id or not client_secret:
        # First try temp_key from session_state
        temp_key = st.session_state.get('temp_key')
        
        # If not found, check URL query parameters
        if not temp_key:
            temp_key = st.query_params.get('state')
        
        if temp_key:
            # Reload temp_storage to get latest
            temp_storage = load_temp_storage()
            if temp_key in temp_storage:
                client_id = temp_storage[temp_key]['client_id']
                client_secret = temp_storage[temp_key]['client_secret']
                # Restore to session_state
                st.session_state.client_id = client_id
                st.session_state.client_secret = client_secret
                st.session_state.temp_key = temp_key
                if st.session_state.get('debug_mode', False):
                    st.write(f"Debug: Restored credentials from temp_storage using key: {temp_key}")
    
    return client_id, client_secret