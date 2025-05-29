import pandas as pd
from pathlib import Path

# Column name mappings
COLUMN_MAPPINGS = {
    'name': 'Instructor Name',
    'title': 'Session Title',
    'start_time': 'Start Time',
    'end_time': 'End Time',
    'duration_hours': 'Duration (Hours)'
}

def clean_instructor_name(name):
    """Clean and standardize instructor names."""
    if pd.isna(name):
        return "Unknown"
    return str(name).strip().title()

def format_instructor_report(df):
    """Format the instructor report with proper column names and totals."""
    # Select and rename columns
    report_df = df[list(COLUMN_MAPPINGS.keys())].copy()
    report_df.columns = list(COLUMN_MAPPINGS.values())
    
    # Format datetime columns
    report_df['Start Time'] = pd.to_datetime(report_df['Start Time']).dt.strftime('%Y-%m-%d %H:%M')
    report_df['End Time'] = pd.to_datetime(report_df['End Time']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Format duration to 2 decimal places
    report_df['Duration (Hours)'] = report_df['Duration (Hours)'].round(2)
    
    # Add total row
    total_row = pd.DataFrame({
        'Instructor Name': ['Total'],
        'Session Title': [''],
        'Start Time': [''],
        'End Time': [''],
        'Duration (Hours)': [report_df['Duration (Hours)'].sum()]
    })
    
    return pd.concat([report_df, total_row], ignore_index=True)

def generate_instructor_reports(events_df, target_month):
    """Generate separate dataframes for each instructor for the target month."""
    # Clean instructor names
    events_df['name'] = events_df['name'].apply(clean_instructor_name)
    
    # Convert start_time to datetime and filter for target month
    events_df['start_time'] = pd.to_datetime(events_df['start_time'], format='ISO8601')
    target_month_events = events_df[events_df['start_time'].dt.strftime('%Y-%m') == target_month]
    
    if target_month_events.empty:
        print(f"No events found for {target_month}")
        return {}
    
    # Group events by instructor and generate reports
    instructor_reports = {}
    for instructor, instructor_events in target_month_events.groupby('name'):
        # Sort events by start time
        instructor_events = instructor_events.sort_values('start_time')
        
        # Format the report
        formatted_report = format_instructor_report(instructor_events)
        
        # Store the report with instructor info
        instructor_reports[instructor] = {
            'report': formatted_report,
            'email': instructor_events['email'].iloc[0] if 'email' in instructor_events.columns else 'no_email'
        }
    
    return instructor_reports 