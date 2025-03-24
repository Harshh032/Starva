import requests
import streamlit as st

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