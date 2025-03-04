import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# Set page configuration
st.set_page_config(
    page_title="Strava Workout Uploader",
    page_icon="🏋️",
    layout="centered"
)

# Initialize session state variables if they don't exist
def init_session_state():
    if 'phase' not in st.session_state:
        st.session_state.phase = 'credentials'
    if 'client_id' not in st.session_state:
        st.session_state.client_id = ''
    if 'client_secret' not in st.session_state:
        st.session_state.client_secret = ''
    if 'redirect_uri' not in st.session_state:
        st.session_state.redirect_uri = 'https://www.example.com'
    if 'auth_code' not in st.session_state:
        st.session_state.auth_code = ''
    if 'auth_success' not in st.session_state:
        st.session_state.auth_success = False
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False

# Function to handle page navigation
def set_phase(phase):
    st.session_state.phase = phase

# Function to save credentials
def save_credentials():
    # Validate inputs before saving
    if not st.session_state.client_id_input:
        st.error("Please enter a Client ID.")
        return
    
    if not st.session_state.client_secret_input:
        st.error("Please enter a Client Secret.")
        return
    
    if not st.session_state.redirect_uri_input:
        st.error("Please enter a Redirect URI.")
        return
    
    try:
        # Test if client_id is a valid integer
        int(st.session_state.client_id_input)
    except ValueError:
        st.error("Client ID must be a number. Please check your Client ID.")
        return
    
    # Store credentials in session state
    st.session_state.client_id = st.session_state.client_id_input
    st.session_state.client_secret = st.session_state.client_secret_input
    st.session_state.redirect_uri = st.session_state.redirect_uri_input
    set_phase('authorization')

# Parse CSV and Extract Details
def parse_csv(file):
    try:
        df = pd.read_csv(file)
        description = ""
        
        for _, row in df.iterrows():
            filtered_row = {col: row[col] for col in df.columns if col.lower() not in ['date', 'athlete']}
            row_data = " | ".join([f"{col}: {val}" for col, val in filtered_row.items()])
            description += f"{row_data}\n"
        
        total_sets = len(df)
        elapsed_time = max(total_sets * 30, 60)
        return description, elapsed_time
    except Exception as e:
        st.error(f"Error parsing CSV: {str(e)}")
        return "Error parsing workout data", 60

# Generate a unique activity name
def generate_unique_name(base_name):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"{base_name} - {timestamp}"

# Function to verify the authorization code
def verify_auth_code():
    if not st.session_state.manual_auth_code:
        st.error("Please enter an authorization code.")
        return False
    
    st.session_state.auth_code = st.session_state.manual_auth_code
    st.session_state.auth_success = True
    set_phase('upload')
    return True

# Get access token
def get_access_token(client_id, client_secret, code, debug=False):
    url = "https://www.strava.com/oauth/token"
    
    if not client_id:
        st.error("Client ID is empty. Please enter a valid Client ID.")
        return None
    
    try:
        client_id_int = int(client_id)
    except ValueError:
        st.error("Client ID must be a number. Please check your Client ID.")
        return None
    
    payload = {
        "client_id": client_id_int,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code"
    }
    
    if debug or st.session_state.debug_mode:
        st.write("Debug - Token Exchange Request:")
        st.write(f"URL: {url}")
        st.write(f"Payload: {payload}")
    
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        if debug or st.session_state.debug_mode:
            st.write("Token Exchange Successful:")
            safe_response = {k: v if k != 'access_token' else v[:10] + '...' for k, v in response.json().items()}
            st.write(safe_response)
        return response.json()["access_token"]
    else:
        st.error(f"Token Exchange Error: {response.text}")
        if debug or st.session_state.debug_mode:
            st.write(f"Response Status: {response.status_code}")
            st.write(f"Response Headers: {response.headers}")
        return None

# Create a Custom Activity
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
    
    if debug or st.session_state.debug_mode:
        st.write("Debug - Create Activity Request:")
        st.write(f"URL: {url}")
        st.write(f"Headers: {headers}")
        st.write(f"Payload: {payload}")
    
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 201:
        if debug or st.session_state.debug_mode:
            st.write("Create Activity Response:")
            st.write(response.json())
        return response.json()
    else:
        st.error(f"Error creating activity: {response.text}")
        if debug or st.session_state.debug_mode:
            st.write(f"Response Status: {response.status_code}")
            st.write(f"Response Headers: {response.headers}")
        return None

# Function to get Strava authorization URL
def get_auth_url():
    client_id = st.session_state.client_id
    redirect_uri = st.session_state.redirect_uri
    scope = "activity:write"
    
    auth_url = (
        f"https://www.strava.com/oauth/authorize?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"approval_prompt=force&"
        f"scope={scope}"
    )
    return auth_url

# Function to handle file upload
def handle_upload():
    if not st.session_state.client_id:
        st.error("Client ID is missing. Please go back to the credentials step.")
        return
    
    if not st.session_state.client_secret:
        st.error("Client Secret is missing. Please go back to the credentials step.")
        return
    
    if not st.session_state.auth_code:
        st.error("No authorization code available. Please authorize with Strava first.")
        return
    
    if not st.session_state.activity_name:
        st.error("Please enter an activity name.")
        return
    
    if st.session_state.uploaded_file is None:
        st.error("No CSV file selected. Please upload a workout CSV file.")
        return
    
    if st.session_state.debug_mode:
        st.write("Debug info:")
        st.write(f"Client ID: '{st.session_state.client_id}'")
        st.write(f"Client Secret: '{st.session_state.client_secret[:3]}...'")
        st.write(f"Auth Code: '{st.session_state.auth_code[:10]}...'")
    
    description, elapsed_time = parse_csv(st.session_state.uploaded_file)
    
    access_token = get_access_token(
        st.session_state.client_id, 
        st.session_state.client_secret, 
        st.session_state.auth_code,
        debug=st.session_state.debug_mode
    )
    
    if not access_token:
        st.error("Failed to get access token. Please check your credentials and try again.")
        return
    
    unique_name = generate_unique_name(st.session_state.activity_name)
    
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    result = create_activity(
        access_token=access_token,
        name=unique_name,
        activity_type="WeightTraining",
        start_date=current_time,
        elapsed_time=elapsed_time,
        description=description,
        debug=st.session_state.debug_mode
    )
    
    if result:
        st.success(f"Activity '{unique_name}' created successfully on Strava!")
        st.markdown(f"[View on Strava](https://www.strava.com/dashboard)", unsafe_allow_html=True)
    else:
        st.error("Error creating activity. Please check that your Strava API limits haven't been exceeded.")

# Main application
def main():
    init_session_state()
    
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
            st.session_state.redirect_uri = 'https://www.example.com'
            st.session_state.auth_code = ''
            st.session_state.auth_success = False
            st.session_state.debug_mode = debug_mode
            st.success("Application has been reset.")
            st.rerun()
    
    if st.session_state.phase == 'credentials':
        st.markdown('### 1. API Credentials', unsafe_allow_html=True)
        
        st.text_input("Strava Client ID:", key="client_id_input", 
                      value=st.session_state.client_id,
                      placeholder="Enter your Strava Client ID")
        
        st.text_input("Strava Client Secret:", key="client_secret_input", 
                      value=st.session_state.client_secret,
                      placeholder="Enter your Strava Client Secret",
                      type="password")
        
        st.text_input("Redirect URI:", key="redirect_uri_input", 
                      value=st.session_state.get('redirect_uri', 'https://www.example.com'),
                      placeholder="Enter your redirect URI (e.g., https://www.example.com)")
        
        st.button("Continue to Authorization", on_click=save_credentials)
        
    elif st.session_state.phase == 'authorization':
        st.markdown('### 2. Manual Authorization', unsafe_allow_html=True)
        
        st.info(f"""
        Client ID: {st.session_state.client_id}
        Redirect URI: {st.session_state.redirect_uri}
        
        Follow these steps to authorize with Strava:
        1. Click the "Open Strava Authorization" button below
        2. Log in to your Strava account if needed
        3. Authorize the app
        4. After authorization, you'll be redirected to {st.session_state.redirect_uri}?code=...
        5. Copy the authorization code from the URL (after "code=" and before "&" or the end)
        6. Paste the code in the field below
        """)
        
        st.markdown("""
        **Important:** Ensure the Redirect URI matches the one registered in your Strava app settings at 
        [Strava API Settings](https://www.strava.com/settings/api).
        """)
        
        auth_url = get_auth_url()
        
        st.markdown(f'<a href="{auth_url}" target="_blank" style="text-decoration:none;">'
                    f'<button style="background-color: #fc4c02; color: white; border: none; padding: 10px 20px; border-radius: 5px;">'
                    f'🔑 Open Strava Authorization</button></a>', unsafe_allow_html=True)
        
        st.text_input("Paste authorization code here:", key="manual_auth_code")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Verify & Continue"):
                if verify_auth_code():
                    st.rerun()
        with col2:
            if st.button("Back to Credentials"):
                set_phase('credentials')
        
        with st.expander("Help: How to find the authorization code"):
            st.markdown(f"""
            After authorizing with Strava, you'll be redirected to a URL like:
                        Copy only the part after `code=` and before the next `&` or the end of the URL.
                        In the example above, you would copy: `1a2b3c4d5e6f7g8h9i0j`

                        Paste this code in the field above and click "Verify & Continue".
                        """)
            
            
    elif st.session_state.phase == 'upload':
        # Upload page
        st.markdown('### 3. Workout Details', unsafe_allow_html=True)
        
        st.info("Verify or update your credentials below:")
        
        # Use temporary variables to ensure pre-filling
        temp_client_id = st.text_input("Strava Client ID:", key="client_id_input_upload", 
                                       value=st.session_state.client_id,
                                       placeholder="Enter your Strava Client ID")
        
        temp_client_secret = st.text_input("Strava Client Secret:", key="client_secret_input_upload", 
                                           value=st.session_state.client_secret,
                                           placeholder="Enter your Strava Client Secret",
                                           type="password")
        
        # Update session state if user modifies credentials
        st.session_state.client_id = temp_client_id
        st.session_state.client_secret = temp_client_secret
        
        st.info(f"""
        You are now connected to Strava as Client ID: {st.session_state.client_id}
        Authorization Code: {st.session_state.auth_code[:10]}...
        """)
        
        st.text_input("Activity Name:", key="activity_name", 
                      placeholder="e.g., Deadlift Session")
        
        # CSV upload with drag and drop
        st.markdown("""
        📄 Drag and drop your CSV file here or click to upload
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Upload CSV file", type=["csv"], key="uploaded_file", label_visibility="collapsed")
        
        if uploaded_file is not None:
            st.success(f"File uploaded: {uploaded_file.name}")
            
            # Display preview of the CSV data
            df = pd.read_csv(uploaded_file)
            st.write("Preview of upload data:")
            st.dataframe(df.head())
            
            # Reset file pointer for later use
            uploaded_file.seek(0)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Upload to Strava", key="upload_button"):
                handle_upload()
                
        with col2:
            if st.button("Back to Authorization"):
                set_phase('authorization')

if __name__ == "__main__":
    main()