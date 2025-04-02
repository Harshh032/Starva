import streamlit as st
import os
import time
from datetime import datetime

from auth.credentials import get_credentials, save_credentials
from auth.oauth import get_access_token, refresh_access_token
from data.parser import parse_csv, generate_unique_name
from api.starva_api import create_activity
from utils.storage import load_temp_storage, save_temp_storage, clean_temp_storage

# Set page configuration
st.set_page_config(
    page_title="Strava Workout Uploader",
    page_icon="🏋️",
    layout="centered"
)

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


# Handle file upload
def handle_upload():
    if 'token_data' not in st.session_state or st.session_state.token_data is None:
        st.error("No token data available. Please authorize with Strava first.")
        return
    
    token_data = st.session_state.token_data
    current_time = int(time.time())
    
    # Check if token is expired and refresh if needed
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
    
    # Validate inputs
    if st.session_state.uploaded_file is None:
        st.error("No CSV file selected. Please upload a workout CSV file.")
        return
    
    # Get selected exercise (if any)
    selected_exercise = st.session_state.get('selected_exercise', None)
    if selected_exercise == "All Exercises":
        selected_exercise = None
    
    # Parse CSV and create activity
    description, elapsed_time, total_weight, total_sets, total_reps, _ = parse_csv(
        st.session_state.uploaded_file, 
        selected_exercise
    )
    
    # Use appropriate naming strategy
    activity_name = st.session_state.activity_name if st.session_state.activity_name else None
    unique_name = generate_unique_name(activity_name, total_weight, total_sets, total_reps, selected_exercise)
    
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


def upload_phase():
    st.markdown('### 3. Workout Details', unsafe_allow_html=True)
    st.info("You are already authorized with Strava. Your credentials are set and shown below for verification.")
    client_id, client_secret = get_credentials()
    st.write(f"**Strava Client ID:** {client_id}")
    st.write(f"**Strava Client Secret:** {'*' * len(client_secret)}")
    st.info(f"Token expires at: {datetime.fromtimestamp(st.session_state.token_data['expires_at']) if st.session_state.token_data else 'N/A'}")
    
    # Upload file first to get exercise options
    st.markdown("🏋️ Drag and drop your CSV file here or click to upload", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"], key="uploaded_file", label_visibility="collapsed")
    
    if uploaded_file:
        st.success(f"File uploaded: {uploaded_file.name}")
        
        try:
            # Get exercise options from the file
            import pandas as pd
            df = pd.read_csv(uploaded_file)
            
            # Preview the data
            st.write("Preview:", df.head())
            
            # Get unique exercises
            exercises = df['Exercise'].unique().tolist()
            exercise_options = ["All Exercises"] + exercises
            
            # Reset file position for later use
            uploaded_file.seek(0)
            
            # Only show exercise selector
            st.selectbox("Select Exercise (or show all):", 
                         options=exercise_options, 
                         key="selected_exercise",
                         index=0)
            
            # Show description preview
            if st.button("Generate Preview"):
                selected_exercise = st.session_state.selected_exercise
                if selected_exercise == "All Exercises":
                    selected_exercise = None
                    
                description, _, total_weight, total_sets, total_reps, _ = parse_csv(
                    uploaded_file, 
                    selected_exercise
                )
                uploaded_file.seek(0)  # Reset position again
                
                # Generate name for activity
                activity_name = generate_unique_name(None, total_weight, total_sets, total_reps, selected_exercise)
                st.session_state.activity_name = activity_name
                
                st.markdown("### Activity Preview")
                st.write(f"**Generated Name:** {activity_name}")
                st.text_area("Description Preview:", value=description, height=300, disabled=True)
                
                # Reset preview when changing selection
                st.session_state.preview_generated = True
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Upload to Strava"):
                    handle_upload()
            with col2:
                if st.button("Back to Authorization"):
                    set_phase('authorization')
                    
        except Exception as e:
            st.error(f"Error processing CSV file: {str(e)}")
            st.info("Please make sure your CSV file has an 'Exercise' column.")
    else:
        st.info("Please upload a CSV file to continue.")

        
def main():
    init_session_state()
    # Clean up old entries in temp_storage
    clean_temp_storage()
    
    redirect_uri = os.getenv("REDIRECT_URI", "https://starva.onrender.com")
    
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
        upload_phase()

if __name__ == "__main__":
    main()
