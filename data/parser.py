# import pandas as pd
# import streamlit as st

# # Parse CSV and extract details for the given activity

# def parse_csv(file, activity_name):
#     try:
#         # Load the CSV
#         df = pd.read_csv(file)
        
#         # Filter by exercise name
#         df = df[df['Exercise'] == activity_name]
        
#         # Normalize column names
#         df.columns = [col.strip().replace(' ', '').replace('(kg)', 'kg') for col in df.columns]

#         # Convert weight to numeric if it exists
#         if 'Weightkg' in df.columns:
#             df['Weightkg'] = df['Weightkg'].astype(str).str.replace('kg', '', regex=False).astype(float)

#         # Extract metrics
#         total_weight = df['Weightkg'].sum() if 'Weightkg' in df.columns else 0
#         total_reps = df['Rep'].sum() if 'Rep' in df.columns else 0
#         total_sets = len(df)

#         # Average metrics calculations
#         metrics = {
#             'MeanVelocity(m/s)': ('Mean Velocity', 'm/s', 2),
#             "PeakVelocity(m/s)": ("Peak Velocity" , 'm/s' , 2),
#             'MeanPower(W)': ('Mean Power', 'W', 0),
#             'PeakPower(W)': ('Peak Power', 'W', 0),
#             'Height(cm)': ('Height', 'cm', 2),
#             'VerticalDistance(cm)': ('Vertical Distance', 'cm', 2)
#         }

#         # Generate metrics summary
#         description = "Workout Summary\n\n"
#         description += f"- Exercise: {activity_name}\n"
#         description += f"- Sets: {total_sets}\n"
#         description += f"- Reps: {total_reps}\n"
#         description += f"- Total Weight: {total_weight:.2f} kg\n\n"

#         description += "Performance Metrics\n"

#         for col, (name, unit, decimals) in metrics.items():
#             if col in df.columns:
#                 print("Hello column : " , col)
#                 avg_value = df[col].mean()
#                 description += f"- **{name}:** {avg_value:.{decimals}f} {unit}\n"

#         # Use a default elapsed time
#         elapsed_time = 0

#         return description, elapsed_time, total_weight, total_sets, total_reps

#     except Exception as e:
#         st.error(f"Error parsing CSV: {str(e)}")
#         return "Error parsing workout data", 60, 0, 0, 0


# # Generate a unique activity name
# def generate_unique_name(base_name, total_weight, total_sets, total_reps):
#     return f"{base_name} - {int(total_weight)}kg TT {total_sets} Sets {int(total_reps)} Reps"



import pandas as pd

# Parse CSV and extract details for the given activity
def parse_csv(file, activity_name):
    try:
        # Load the CSV
        df = pd.read_csv(file)
        
        # Filter by exercise name
        df = df[df['Exercise'] == activity_name]
        print("Hello acitvity here : " , activity_name)
        
        # Normalize column names (remove spaces, standardize)
        df.columns = [col.strip().replace(' ', '').replace('(kg)', 'kg') for col in df.columns]

        # Handle weight column (could be 'Load' or 'Weightkg')
        weight_col = None
        if 'Load' in df.columns:
            weight_col = 'Load'
        elif 'Weightkg' in df.columns:
            weight_col = 'Weightkg'
        
        if weight_col:
            df[weight_col] = df[weight_col].astype(str).str.replace('kg', '', regex=False).astype(float)
            total_weight = df[weight_col].sum()
        else:
            total_weight = 0  # Default if no weight column is found

        # Handle reps and sets
        total_reps = df['Reps'].sum() if 'Reps' in df.columns else df['Rep'].sum() if 'Rep' in df.columns else 0
        total_sets = df['Set'].nunique() if 'Set' in df.columns else len(df)

        # Define possible metrics based on column names in both CSVs
        metrics = {
            'Average': ('Mean Velocity', 'm/s', 2),          
            'MeanVelocity(m/s)': ('Mean Velocity', 'm/s', 2), 
            'Best': ('Peak Velocity', 'm/s', 2),              
            'PeakVelocity(m/s)': ('Peak Velocity', 'm/s', 2), 
            'MeanPower(W)': ('Mean Power', 'W', 0),           
            'PeakPower(W)': ('Peak Power', 'W', 0),           
            'Height(cm)': ('Height', 'cm', 2),                
            'VerticalDistance(cm)': ('Vertical Distance', 'cm', 2)

        }

        # Generate metrics summary
        description = "Workout Summary\n\n"
        description += f"- Exercise: {activity_name}\n"
        description += f"- Sets: {total_sets}\n"
        description += f"- Reps: {total_reps}\n\n"
        # description += f"- Total Weight: {total_weight:.2f} kg\n\n"

        description += "Performance Metrics\n"

        # Dynamically include metrics present in the CSV
        for col, (name, unit, decimals) in metrics.items():
            if col in df.columns:
                avg_value = df[col].mean()
                description += f"- **{name}:** {avg_value:.{decimals}f} {unit}\n"

        # Default elapsed time (could be improved with actual time calculation if data is available)
        elapsed_time = 0

        return description, elapsed_time, total_weight, total_sets, total_reps

    except Exception as e:
        # st.error(f"Error parsing CSV: {str(e)}")
        return "Error parsing workout data", 60, 0, 0, 0

# Generate a unique activity name
def generate_unique_name(base_name, total_weight, total_sets, total_reps):
    return f"{base_name} - {int(total_weight)}kg TT {total_sets} Sets {int(total_reps)} Reps"



