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
    
    try:
        # Test if client_id is a valid integer
        int(st.session_state.client_id_input)
    except ValueError:
        st.error("Client ID must be a number. Please check your Client ID.")
        return
    
    # Store credentials in session state
    st.session_state.client_id = st.session_state.client_id_input
    st.session_state.client_secret = st.session_state.client_secret_input
    set_phase('authorization')

# Parse CSV and Extract Details (Flexible Parsing)
# Parse CSV and Extract Details (Exclude 'date' and 'athlete' columns)
def parse_csv(file):
    try:
        df = pd.read_csv(file)
        description = ""
        
        # Dynamically parse all columns except 'date' and 'athlete'
        for _, row in df.iterrows():
            # Filter out unwanted columns
            filtered_row = {col: row[col] for col in df.columns if col.lower() not in ['date', 'athlete']}
            
            # Convert the filtered row into a string representation
            row_data = " | ".join([f"{col}: {val}" for col, val in filtered_row.items()])
            description += f"{row_data}\n"
        
        total_sets = len(df)
        elapsed_time = max(total_sets * 30, 60)  # Minimum 60 seconds, or 30 seconds per set
        return description, elapsed_time
    except Exception as e:
        st.error(f"Error parsing CSV: {str(e)}")
        return "Error parsing workout data", 60

# Generate a unique activity name
def generate_unique_name(base_name):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"{base_name} - {timestamp}"

# Get access token
def get_access_token(client_id, client_secret, code, debug=False):
    url = "https://www.strava.com/oauth/token"
    
    # Check if client_id is empty
    if not client_id:
        st.error("Client ID is empty. Please enter a valid Client ID.")
        return None
    
    try:
        # Try to convert client_id to integer
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
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "name": name,
        "type": activity_type,
        "start_date_local": start_date,
        "elapsed_time": elapsed_time,  # in seconds
        "description": description     # optional
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


def get_current_url():
    """
    Hardcode the deployed URL for redirection.
    """
    # Replace with your actual deployment URL
    return "https://stravaflexa.onrender.com/"
# Function to get Strava authorization URL
def get_auth_url():
    client_id = st.session_state.client_id
    
    # Get current URL for redirect (works in both local and deployed environments)
    current_url = get_current_url()
    
    # Store the current URL in session state for later use
    st.session_state.redirect_uri = current_url
    
    scope = "activity:write"
    
    auth_url = (
        f"https://www.strava.com/oauth/authorize?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"redirect_uri={current_url}&"
        f"approval_prompt=force&"
        f"scope={scope}"
    )
    
    if st.session_state.debug_mode:
        st.write(f"Auth URL generated with redirect to: {current_url}")
    
    return auth_url

# Check for authorization code in URL
def check_url_for_auth_code():
    query_params = st.query_params
    if 'code' in query_params:
        st.session_state.auth_code = query_params['code']
        st.session_state.auth_success = True
        st.query_params.clear()
        set_phase('upload')
        return True
    return False

# Function to handle file upload
def handle_upload():
    # Verify that we have all required data
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
    
    # Debug section
    if st.session_state.debug_mode:
        st.write("Debug info:")
        st.write(f"Client ID: '{st.session_state.client_id}'")
        st.write(f"Client Secret: '{st.session_state.client_secret[:3]}...'")
        st.write(f"Auth Code: '{st.session_state.auth_code[:10]}...'")
    
    # Parse CSV
    description, elapsed_time = parse_csv(st.session_state.uploaded_file)
    
    # Get access token
    access_token = get_access_token(
        st.session_state.client_id, 
        st.session_state.client_secret, 
        st.session_state.auth_code,
        debug=st.session_state.debug_mode
    )
    
    if not access_token:
        st.error("Failed to get access token. Please check your credentials and try again.")
        return
    
    # Generate a unique activity name
    unique_name = generate_unique_name(st.session_state.activity_name)
    
    # Create the activity
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
    
    # App settings in sidebar
    with st.sidebar:
        st.title("App Settings")
        st.session_state.debug_mode = st.toggle("Debug Mode", value=st.session_state.debug_mode)
        
        if st.session_state.debug_mode:
            st.info("Debug mode is enabled. Detailed request and response information will be shown.")
        
        st.divider()
        
        # Reset button
        if st.button("Reset Application"):
            for key in list(st.session_state.keys()):
                if key != 'debug_mode':  # Preserve debug setting
                    del st.session_state[key]
            st.session_state.phase = 'credentials'
            st.session_state.client_id = ''
            st.session_state.client_secret = ''
            st.session_state.auth_code = ''
            st.session_state.auth_success = False
            st.success("Application has been reset.")
            st.rerun()
    
    # Check if authorization code is in URL
    auth_code_in_url = check_url_for_auth_code()
    
    # Show success message if authorization was successful
    if st.session_state.auth_success and auth_code_in_url:
        st.success("Authorization successful! Your code has been captured automatically.")
        time.sleep(2)  # Give user time to see the message
    
    # Determine which page to show
    if st.session_state.phase == 'credentials':
        # Credentials page
        st.markdown('### 1. API Credentials', unsafe_allow_html=True)
        
        st.text_input("Strava Client ID:", key="client_id_input", 
                      value=st.session_state.client_id,
                      placeholder="Enter your Strava Client ID")
        
        st.text_input("Strava Client Secret:", key="client_secret_input", 
                      value=st.session_state.client_secret,
                      placeholder="Enter your Strava Client Secret",
                      type="password")
        
        st.button("Continue to Authorization", on_click=save_credentials)
        
    elif st.session_state.phase == 'authorization':
        # Authorization page
        st.markdown('### 2. Authorization', unsafe_allow_html=True)
        
        st.info(f"""
        Client ID: {st.session_state.client_id}
        
        Click the button below to connect to your Strava account.
        **Important:** Ensure the authorization process completes in the same browser tab.
        """)
        
        auth_url = get_auth_url()
        st.markdown(f'<a href="{auth_url}" target="_self" style="text-decoration:none;">'
                    f'<button style="background-color: #fc4c02; color: white; border: none; padding: 10px 20px; border-radius: 5px;">'
                    f'🔑 Authenticate with Strava</button></a>', unsafe_allow_html=True)
        
        if st.button("Back to Credentials"):
            set_phase('credentials')
            
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