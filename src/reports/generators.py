import pandas as pd
from pathlib import Path

# Column name mappings
COLUMN_MAPPINGS = {
    'name': 'Faculty Name',
    'title': 'Session Title',
    'start_time': 'Start Time',
    'end_time': 'End Time',
    'duration_hours': 'Duration (Hours)',
    'activity_type': 'Activity Type'
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

def format_tutor_report(df):
    """Format the tutor report with proper column names and totals."""
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

def format_faculty_report(df):
    """Format the faculty report with proper column names and totals."""
    # Select and rename columns
    report_df = df[list(COLUMN_MAPPINGS.keys())].copy()
    report_df.columns = list(COLUMN_MAPPINGS.values())
    
    # Format datetime columns
    report_df['Start Time'] = pd.to_datetime(report_df['Start Time']).dt.strftime('%Y-%m-%d %H:%M')
    report_df['End Time'] = pd.to_datetime(report_df['End Time']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Format duration to 2 decimal places
    report_df['Duration (Hours)'] = report_df['Duration (Hours)'].round(2)
    
    # Sort by activity type, then by start time
    report_df = report_df.sort_values(['Activity Type', 'Start Time'])
    
    # Add total row
    total_row = pd.DataFrame({
        'Faculty Name': ['Total'],
        'Session Title': [''],
        'Start Time': [''],
        'End Time': [''],
        'Duration (Hours)': [report_df['Duration (Hours)'].sum()],
        'Activity Type': ['']
    })
    
    return pd.concat([report_df, total_row], ignore_index=True)

def duplicate_events_for_testing(events_df, source_email, target_email):
    """Duplicate events from one instructor to another for testing purposes."""
    # Get source instructor's events
    source_events = events_df[events_df['email'] == source_email].copy()
    
    if source_events.empty:
        print(f"No events found for source instructor {source_email}")
        return events_df
    
    # Create a copy of the events for the target instructor
    target_events = source_events.copy()
    target_events['email'] = target_email
    target_events['name'] = target_email.split('@')[0]  # Use email prefix as name
    
    # Combine original and duplicated events
    return pd.concat([events_df, target_events], ignore_index=True)

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

def generate_tutor_reports(events_df, target_month):
    """Generate separate dataframes for each tutor for the target month."""
    # Clean tutor names
    events_df['name'] = events_df['name'].apply(clean_instructor_name)
    
    # Convert start_time to datetime and filter for target month
    events_df['start_time'] = pd.to_datetime(events_df['start_time'], format='ISO8601')
    target_month_events = events_df[events_df['start_time'].dt.strftime('%Y-%m') == target_month]
    
    if target_month_events.empty:
        print(f"No tutoring sessions found for {target_month}")
        return {}
    
    # Group events by tutor and generate reports
    tutor_reports = {}
    for tutor, tutor_events in target_month_events.groupby('name'):
        # Sort events by start time
        tutor_events = tutor_events.sort_values('start_time')
        
        # Format the report
        formatted_report = format_tutor_report(tutor_events)
        
        # Store the report with tutor info
        tutor_reports[tutor] = {
            'report': formatted_report,
            'email': tutor_events['email'].iloc[0] if 'email' in tutor_events.columns else 'no_email'
        }
    
    return tutor_reports

def generate_faculty_reports(instructor_events_df, tutor_events_df, target_month):
    """Generate unified faculty reports combining instruction and tutoring activities."""
    # Handle None DataFrames
    if instructor_events_df is None:
        instructor_events_df = pd.DataFrame()
    if tutor_events_df is None:
        tutor_events_df = pd.DataFrame()
    
    # If both are empty, return empty dict
    if instructor_events_df.empty and tutor_events_df.empty:
        print(f"No events found for {target_month}")
        return {}
    
    # Clean faculty names
    if not instructor_events_df.empty:
        instructor_events_df['name'] = instructor_events_df['name'].apply(clean_instructor_name)
    if not tutor_events_df.empty:
        tutor_events_df['name'] = tutor_events_df['name'].apply(clean_instructor_name)
    
    # Add activity type column
    if not instructor_events_df.empty:
        instructor_events_df['activity_type'] = 'instruction'
    if not tutor_events_df.empty:
        tutor_events_df['activity_type'] = 'tutoring'
    
    # Convert start_time to datetime and filter for target month
    if not instructor_events_df.empty:
        instructor_events_df['start_time'] = pd.to_datetime(instructor_events_df['start_time'], format='ISO8601')
        instructor_month_events = instructor_events_df[instructor_events_df['start_time'].dt.strftime('%Y-%m') == target_month]
    else:
        instructor_month_events = pd.DataFrame()
    
    if not tutor_events_df.empty:
        tutor_events_df['start_time'] = pd.to_datetime(tutor_events_df['start_time'], format='ISO8601')
        tutor_month_events = tutor_events_df[tutor_events_df['start_time'].dt.strftime('%Y-%m') == target_month]
    else:
        tutor_month_events = pd.DataFrame()
    
    # Combine all events
    all_events = pd.concat([instructor_month_events, tutor_month_events], ignore_index=True)
    
    if all_events.empty:
        print(f"No events found for {target_month}")
        return {}
    
    # Group events by faculty member and generate reports
    faculty_reports = {}
    for faculty_member, faculty_events in all_events.groupby('name'):
        # Sort events by start time
        faculty_events = faculty_events.sort_values('start_time')
        
        # Format the report
        formatted_report = format_faculty_report(faculty_events)
        
        # Store the report with faculty info
        faculty_reports[faculty_member] = {
            'report': formatted_report,
            'email': faculty_events['email'].iloc[0] if 'email' in faculty_events.columns else 'no_email'
        }
    
    return faculty_reports 