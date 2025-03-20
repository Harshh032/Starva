import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import os
import uuid
import json
import tempfile

# Set page configuration
st.set_page_config(
    page_title="Strava Workout Uploader",
    page_icon="🏋️",
    layout="centered"
)

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

# Global temp_storage variable initialized from file
temp_storage = load_temp_storage()

# Initialize session state variables
def init_session_state():
    if 'phase' not in st.session_state:
        st.session_state.phase = 'credentials'
    if 'client_id' not in st.session_state:
        st.session_state.client_id = ''
    if 'client_secret' not in st.session_state:
        st.session_state.client_secret = ''
    if 'token_data' not in st.session_state:
        st.session_state.token_data = None
    if 'auth_success' not in st.session_state:
        st.session_state.auth_success = False
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False
    if 'temp_key' not in st.session_state:
        st.session_state.temp_key = None
    
    # Check if we're returning from OAuth redirect with state parameter
    query_params = st.query_params
    if "state" in query_params and "code" in query_params:
        state_param = query_params["state"]
        temp_storage = load_temp_storage()  # Reload to get latest
        if state_param in temp_storage:
            # Restore credentials from temp_storage using state parameter
            st.session_state.temp_key = state_param
            st.session_state.client_id = temp_storage[state_param]['client_id']
            st.session_state.client_secret = temp_storage[state_param]['client_secret']
            st.session_state.phase = 'authorization'  # Ensure we're in authorization phase

# Function to handle page navigation
def set_phase(phase):
    st.session_state.phase = phase

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
    set_phase('authorization')

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
                if st.session_state.debug_mode:
                    st.write(f"Debug: Restored credentials from temp_storage using key: {temp_key}")
    
    return client_id, client_secret

# Parse CSV and extract details
def parse_csv(file):
    try:
        df = pd.read_csv(file)
        # Normalize column names by stripping spaces and handling variations
        df.columns = [col.strip().replace(' ', '').replace('(kg)', 'kg') for col in df.columns]
        if 'Load' in df.columns:
            df['Load'] = df['Load'].str.extract(r'([\d.]+)\s*kg', expand=False).astype(float)
            total_weight = df['Load'].sum()
        elif 'Weight' in df.columns:
            df['Weight'] = df['Weight'].str.extract(r'([\d.]+)\s*kg', expand=False).astype(float)
            total_weight = df['Weight'].sum()
        elif 'Loadkg' in df.columns:
            df['Loadkg'] = df['Loadkg)'].str.extract(r'([\d.]+)\s*kg', expand=False).astype(float)
            total_weight = df['Loadkg'].sum()
        elif 'Weightkg' in df.columns:
            df['Weightkg'] = df['Weightkg'].str.extract(r'([\d.]+)\s*kg', expand=False).astype(float)
            total_weight = df['Weightkg'].sum()
        else:
            total_weight = 0
        if 'Reps' in df.columns:
            total_reps = df['Reps'].sum()
        elif 'Rep' in df.columns:
            total_reps = df['Rep'].sum()
        else:
            total_reps = 0
        total_sets = len(df)
        description = ""
        for _, row in df.iterrows():
            filtered_row = {col: row[col] for col in df.columns if col.lower() not in ['date', 'athlete']}
            row_data = " | ".join([f"{col}: {val}" for col, val in filtered_row.items()])
            description += f"{row_data}\n"
        # elapsed_time = max(total_sets * 30, 60)
        elapsed_time = 0
        return description, elapsed_time, total_weight, total_sets, total_reps
    except Exception as e:
        st.error(f"Error parsing CSV: {str(e)}")
        return "Error parsing workout data", 60, 0, 0, 0

# Generate a unique activity name
def generate_unique_name(base_name, total_weight, total_sets, total_reps):
    return f"{base_name} - {total_weight}kg TT {total_sets} Sets {total_reps} Reps"

# Get access token and refresh token
def get_access_token(client_id, client_secret, code, debug=False):
    url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": int(client_id),
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code"
    }
    if debug:
        st.write("Debug - Token Exchange Request:", payload)
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        token_data = response.json()
        if debug:
            safe_token_data = {k: v if k != 'access_token' else v[:10] + '...' for k, v in token_data.items()}
            st.write("Token Exchange Successful:", safe_token_data)
        return token_data
    else:
        st.error(f"Token Exchange Error: {response.text}")
        return None

# Refresh access token
def refresh_access_token(client_id, client_secret, refresh_token, debug=False):
    url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": int(client_id),
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        token_data = response.json()
        if debug:
            safe_token_data = {k: v if k != 'access_token' else v[:10] + '...' for k, v in token_data.items()}
            st.write("Token Refresh Successful:", safe_token_data)
        return token_data
    else:
        st.error(f"Token Refresh Error: {response.text}")
        return None

# Create a custom activity
def create_activity(access_token, name, activity_type, start_date, elapsed_time, description=None, debug=False):
    url = "https://www.strava.com/api/v3/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "name": name,
        "type": activity_type,
        "start_date_local": start_date,
        "elapsed_time": elapsed_time,
        "description": description
    }
    if debug:
        st.write("Debug - Create Activity Request:", payload)
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 201:
        if debug:
            st.write("Create Activity Response:", response.json())
        return response.json()
    else:
        st.error(f"Error creating activity: {response.text}")
        return None

# Handle file upload
def handle_upload():
    if 'token_data' not in st.session_state or st.session_state.token_data is None:
        st.error("No token data available. Please authorize with Strava first.")
        return
    token_data = st.session_state.token_data
    current_time = int(time.time())
    if current_time >= token_data['expires_at']:
        client_id, client_secret = get_credentials()
        if not client_id or not client_secret:
            st.error("Credentials missing. Please re-enter them in the Credentials phase.")
            set_phase('credentials')
            return
        new_token_data = refresh_access_token(
            client_id,
            client_secret,
            token_data['refresh_token'],
            debug=st.session_state.debug_mode
        )
        if new_token_data:
            st.session_state.token_data = new_token_data
            access_token = new_token_data['access_token']
        else:
            st.error("Failed to refresh access token. Please re-authorize with Strava.")
            return
    else:
        access_token = token_data['access_token']
    if not st.session_state.activity_name:
        st.error("Please enter an activity name.")
        return
    if st.session_state.uploaded_file is None:
        st.error("No CSV file selected. Please upload a workout CSV file.")
        return
    description, elapsed_time, total_weight, total_sets, total_reps = parse_csv(st.session_state.uploaded_file)
    unique_name = generate_unique_name(st.session_state.activity_name, total_weight, total_sets, total_reps)
    current_time_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    result = create_activity(
        access_token=access_token,
        name=unique_name,
        activity_type="WeightTraining",
        start_date=current_time_str,
        elapsed_time=elapsed_time,
        description=description,
        debug=st.session_state.debug_mode
    )
    if result:
        st.success(f"Activity '{unique_name}' created successfully on Strava!")
        st.markdown("[View on Strava](https://www.strava.com/dashboard)", unsafe_allow_html=True)
    else:
        st.error("Error creating activity. Check your Strava API limits.")

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

# Main application
def main():
    init_session_state()
    # Clean up old entries in temp_storage
    clean_temp_storage()
    
    redirect_uri = os.getenv("REDIRECT_URI", "https://stravaflexa.onrender.com/")
    
    # Process authorization code from redirect
    if st.session_state.phase == 'authorization':
        query_params = st.query_params
        if "code" in query_params:
            client_id, client_secret = get_credentials()
            if not client_id or not client_secret:
                st.error("Credentials could not be retrieved. Please re-enter them.")
                set_phase('credentials')
            else:
                code = query_params["code"]
                token_data = get_access_token(client_id, client_secret, code, debug=st.session_state.debug_mode)
                if token_data:
                    st.session_state.token_data = token_data
                    st.session_state.auth_success = True
                    
                    # Clean up temp_storage after successful token retrieval
                    temp_key = st.session_state.get('temp_key')
                    if temp_key:
                        temp_storage = load_temp_storage()
                        if temp_key in temp_storage:
                            del temp_storage[temp_key]
                            save_temp_storage(temp_storage)
                    
                    set_phase('upload')
                else:
                    st.error("Failed to get access token. Please try authorizing again.")
    
    # Sidebar settings
    with st.sidebar:
        st.title("App Settings")
        st.session_state.debug_mode = st.toggle("Debug Mode", value=st.session_state.debug_mode)
        if st.session_state.debug_mode:
            st.info("Debug mode is enabled. Detailed request and response information will be shown.")
        st.divider()
        if st.button("Reset Application"):
            debug_mode = st.session_state.debug_mode
            for key in list(st.session_state.keys()):
                if key != 'debug_mode':
                    del st.session_state[key]
            st.session_state.phase = 'credentials'
            st.session_state.client_id = ''
            st.session_state.client_secret = ''
            st.session_state.token_data = None
            st.session_state.auth_success = False
            st.session_state.debug_mode = debug_mode
            
            # Clear temp_storage on reset
            temp_storage = load_temp_storage()
            temp_storage.clear()
            save_temp_storage(temp_storage)
            
            st.success("Application has been reset.")
            st.rerun()
    
    # Credentials phase
    if st.session_state.phase == 'credentials':
        st.markdown('### 1. API Credentials', unsafe_allow_html=True)
        st.text_input("Strava Client ID:", key="client_id_input", value=st.session_state.client_id, placeholder="Enter your Strava Client ID")
        st.text_input("Strava Client Secret:", key="client_secret_input", value=st.session_state.client_secret, placeholder="Enter your Strava Client Secret", type="password")
        st.button("Continue to Authorization", on_click=save_credentials)
    
    # Authorization phase
    elif st.session_state.phase == 'authorization':
        st.markdown('### 2. Authorize with Strava', unsafe_allow_html=True)
        temp_key = st.session_state.get('temp_key', '')
        auth_url = f"https://www.strava.com/oauth/authorize?client_id={st.session_state.client_id}&response_type=code&redirect_uri={redirect_uri}&approval_prompt=force&scope=activity:write&state={temp_key}"
        st.info(f"""
        **Client ID:** {st.session_state.client_id}
        To authorize:
        1. Click "Authorize with Strava" below.
        2. Log in to Strava and click "Authorize".
        3. You will be redirected back here automatically.
        """)
        st.markdown(f'''
            <a href="{auth_url}" target="_self" style="display: inline-block; padding: 10px 20px; background-color: #fc5200; color: white; text-align: center; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">Authorize with Strava</a>
        ''', unsafe_allow_html=True)
        st.markdown("#### Or Paste Authorization Code (if automatic capture fails)")
        st.text_input("Authorization Code:", key="manual_auth_code", placeholder="e.g., abc123def456ghi789")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Verify & Continue"):
                if st.session_state.manual_auth_code:
                    client_id, client_secret = get_credentials()
                    if not client_id or not client_secret:
                        st.error("Credentials missing. Please re-enter them.")
                        set_phase('credentials')
                    else:
                        token_data = get_access_token(client_id, client_secret, st.session_state.manual_auth_code, debug=st.session_state.debug_mode)
                        if token_data:
                            st.session_state.token_data = token_data
                            st.session_state.auth_success = True
                            
                            # Clean up temp_storage after successful token retrieval
                            temp_key = st.session_state.get('temp_key')
                            if temp_key:
                                temp_storage = load_temp_storage()
                                if temp_key in temp_storage:
                                    del temp_storage[temp_key]
                                    save_temp_storage(temp_storage)
                            
                            set_phase('upload')
                        else:
                            st.error("Invalid authorization code.")
        with col2:
            if st.button("Back to Credentials"):
                set_phase('credentials')
    
    # Upload phase
    elif st.session_state.phase == 'upload':
        st.markdown('### 3. Workout Details', unsafe_allow_html=True)
        st.info("You are already authorized with Strava. Your credentials are set and shown below for verification.")
        client_id, client_secret = get_credentials()
        st.write(f"**Strava Client ID:** {client_id}")
        st.write(f"**Strava Client Secret:** {'*' * len(client_secret)}")
        st.info(f"Token expires at: {datetime.fromtimestamp(st.session_state.token_data['expires_at']) if st.session_state.token_data else 'N/A'}")
        st.text_input("Activity Name:", key="activity_name", placeholder="e.g., Deadlift Session")
        st.markdown("🏋️ Drag and drop your CSV file here or click to upload", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload CSV file", type=["csv"], key="uploaded_file", label_visibility="collapsed")
        if uploaded_file:
            st.success(f"File uploaded: {uploaded_file.name}")
            df = pd.read_csv(uploaded_file)
            st.write("Preview:", df.head())
            uploaded_file.seek(0)
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Upload to Strava"):
                handle_upload()
        with col2:
            if st.button("Back to Authorization"):
                set_phase('authorization')

if __name__ == "__main__":
    main()