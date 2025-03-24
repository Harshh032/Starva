import requests
import streamlit as st

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