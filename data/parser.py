import pandas as pd

def parse_csv(file, selected_exercise=None):
    try:
        
        # Load the CSV
        df = pd.read_csv(file)
        
        # Normalize column names (remove spaces, standardize)
        df.columns = [col.strip().replace(' ', '').replace('(kg)', 'kg') for col in df.columns]

        # Handle weight column (could be 'Load' or 'Weightkg')
        weight_col = None
        if 'Load' in df.columns:
            weight_col = 'Load'
        elif 'Weightkg' in df.columns:
            weight_col = 'Weightkg'
        
        # Convert weight column to numeric if it exists
        if weight_col:
            df[weight_col] = df[weight_col].astype(str).str.replace('kg', '', regex=False).astype(float)
        
        # Get unique exercises for potential selection
        all_exercises = df['Exercise'].unique()
        
        # Filter by specific exercise if selected
        if selected_exercise and selected_exercise in all_exercises:
            working_df = df[df['Exercise'] == selected_exercise]
            is_single_exercise = True
        else:
            working_df = df
            is_single_exercise = False
        
        # Calculate totals based on filtered dataframe
        total_weight = working_df[weight_col].sum() if weight_col else 0
        total_sets = working_df['Set'].nunique() if 'Set' in working_df.columns else len(working_df)
        total_reps = working_df['Reps'].sum() if 'Reps' in working_df.columns else working_df['Rep'].sum() if 'Rep' in working_df.columns else 0
        
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

        # Generate description with appropriate details
        description = "Workout Summary\n\n"
        
        if is_single_exercise:
            # Single exercise mode
            description += f"- Exercise: {selected_exercise}\n"
            description += f"- Sets: {total_sets}\n"
            description += f"- Reps: {total_reps}\n"
            description += f"- Total Weight: {total_weight:.2f} kg\n\n"
            
            # Add performance metrics for this exercise
            description += "Performance Metrics\n"
            for col, (name, unit, decimals) in metrics.items():
                if col in working_df.columns and not working_df[col].isnull().all():
                    avg_value = working_df[col].mean()
                    description += f"- {name}: {avg_value:.{decimals}f} {unit}\n"
        else:
            # Multiple exercises mode
            exercises_in_df = working_df['Exercise'].unique()
            description += f"- Total Exercises: {len(exercises_in_df)}\n"
            description += f"- Total Sets: {total_sets}\n"
            description += f"- Total Reps: {total_reps}\n"
            description += f"- Total Weight: {total_weight:.2f} kg\n\n"
            
            # Add details for each exercise
            description += "Exercise Details\n"
            
            for exercise in exercises_in_df:
                exercise_df = working_df[working_df['Exercise'] == exercise]
                
                # Calculate exercise-specific totals
                ex_sets = exercise_df['Set'].nunique() if 'Set' in exercise_df.columns else len(exercise_df)
                ex_reps = exercise_df['Reps'].sum() if 'Reps' in exercise_df.columns else exercise_df['Rep'].sum() if 'Rep' in exercise_df.columns else 0
                ex_weight = exercise_df[weight_col].sum() if weight_col else 0
                
                description += f"\n## {exercise}\n"
                description += f"- Sets: {ex_sets}\n"
                description += f"- Reps: {ex_reps}\n"
                description += f"- Total Weight: {ex_weight:.2f} kg\n"
                
                # Add performance metrics for this exercise
                description += "- Performance Metrics:\n"
                for col, (name, unit, decimals) in metrics.items():
                    if col in exercise_df.columns and not exercise_df[col].isnull().all():
                        avg_value = exercise_df[col].mean()
                        description += f"  • {name}: {avg_value:.{decimals}f} {unit}\n"

        # Default elapsed time (could be improved with actual time calculation if data is available)
        elapsed_time = 600  # Default to 10 minutes

        return description, elapsed_time, total_weight, total_sets, total_reps, all_exercises

    except Exception as e:
        # Add print statement for debugging
        print(f"Error parsing CSV: {str(e)}")
        return f"Error parsing workout data: {str(e)}", 60, 0, 0, 0, []

# Generate a unique activity name based on selection mode
def generate_unique_name(base_name, total_weight, total_sets, total_reps, selected_exercise=None):
    from datetime import datetime
    date_str = datetime.now().strftime("%b %d")
    
    if selected_exercise:
        # Single exercise mode
        return f"{selected_exercise} - {date_str} - {int(total_weight)}kg {total_sets}S {int(total_reps)}R"
    elif base_name:
        # Multiple exercises with custom name
        return f"{base_name} - {date_str} - {int(total_weight)}kg {total_sets}S {int(total_reps)}R"
    else:
        # Multiple exercises with default name
        return f"FLEX {date_str} - {int(total_weight)}kg {total_sets}S {int(total_reps)}R"
