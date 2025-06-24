import pandas as pd
from datetime import datetime
import os

# Constants
HOURLY_RATE = 72
TARGET_PROGRAMS = ['DATA_SCIENCE', 'CYBER', 'WEB']
METRIC_TYPES = {
    'event_count': 'Number of events',
    'hour_count': 'Total hours',
    'cost': 'Total cost ($)'
}

def read_input_files():
    """Read all required input files."""
    events_df = pd.read_csv('output/events_list.csv')
    event_to_program_df = pd.read_csv('data/raw/event_id_to_program.csv')
    event_to_course_df = pd.read_csv('data/raw/event_id_to_course_id.csv')
    course_metadata_df = pd.read_csv('data/raw/course_metadata.csv')
    return events_df, event_to_program_df, event_to_course_df, course_metadata_df

def create_program_mappings(event_to_program_df, event_to_course_df, course_metadata_df):
    """Create program mappings from both sources."""
    # Create course-based mapping
    course_mapping_df = event_to_course_df.merge(
        course_metadata_df,
        left_on='course_id',
        right_on='id',
        how='left'
    )[['ms_event_id', 'domain']]
    
    # Combine both mapping sources
    return [event_to_program_df, course_mapping_df]

def prepare_events_data(events_df, program_mappings):
    """Prepare and merge events data with program mappings."""
    # Combine all program mappings
    combined_program_df = pd.concat(
        [df[['ms_event_id', 'domain']] for df in program_mappings],
        ignore_index=True
    ).drop_duplicates(subset=['ms_event_id'])
    
    # Convert start_time to datetime and extract month
    events_df['start_time'] = pd.to_datetime(events_df['start_time'], format='ISO8601')
    events_df['month'] = events_df['start_time'].dt.strftime('%Y-%m')
    
    # Merge events with program information
    return events_df.merge(
        combined_program_df,
        on='ms_event_id',
        how='left'
    )

def calculate_monthly_stats(merged_df):
    """Calculate monthly statistics for each program."""
    # Filter for target programs
    filtered_df = merged_df[merged_df['domain'].isin(TARGET_PROGRAMS)]
    
    # Calculate statistics
    monthly_stats = filtered_df.groupby(['month', 'domain']).agg({
        'ms_event_id': 'count',
        'duration_hours': 'sum'
    }).reset_index()
    
    # Rename columns
    monthly_stats.columns = ['month', 'program', 'event_count', 'total_hours']
    return monthly_stats.sort_values(['month', 'program'])

def create_metric_matrices(monthly_stats):
    """Create matrices for different metrics."""
    # Create base matrices
    event_count_matrix = monthly_stats.pivot(
        index='program',
        columns='month',
        values='event_count'
    ).fillna(0)
    
    hours_matrix = monthly_stats.pivot(
        index='program',
        columns='month',
        values='total_hours'
    ).fillna(0)
    
    # Calculate cost matrix
    cost_matrix = hours_matrix * HOURLY_RATE
    
    return event_count_matrix, hours_matrix, cost_matrix

def combine_matrices(event_count_matrix, hours_matrix, cost_matrix):
    """Combine all metric matrices into a single dataframe."""
    # Add metric type to each matrix
    matrices = {
        'event_count': event_count_matrix,
        'hour_count': hours_matrix,
        'cost': cost_matrix
    }
    
    # Combine all matrices
    combined = pd.concat([
        df.assign(metric_type=metric_type)
        for metric_type, df in matrices.items()
    ])
    
    # Reset index and reorder columns
    combined = combined.reset_index()
    cols = ['program', 'metric_type'] + [col for col in combined.columns if col not in ['program', 'metric_type']]
    return combined[cols]

def save_output_files(combined_matrix, monthly_stats, unmatched_events):
    """Save all output files."""
    combined_matrix.to_csv('output/combined_program_stats.csv', index=False)
    monthly_stats.to_csv('output/monthly_program_stats.csv', index=False)
    unmatched_events.to_csv('output/no_calendar_match.csv', index=False)

def analyze_program_events(program_mappings=None):
    """
    Analyze program events using one or more program mapping dataframes.
    
    Args:
        program_mappings (list of pd.DataFrame, optional): List of dataframes containing program mappings.
            Each dataframe should have at least 'ms_event_id' and 'domain' columns.
            If None, will read from input files for backward compatibility.
    """
    # Read input files if no mappings provided
    if program_mappings is None:
        events_df, event_to_program_df, event_to_course_df, course_metadata_df = read_input_files()
        program_mappings = create_program_mappings(
            event_to_program_df, 
            event_to_course_df, 
            course_metadata_df
        )
    
    # Prepare and merge data
    merged_df = prepare_events_data(events_df, program_mappings)
    
    # Find unmatched events
    unmatched_events = merged_df[merged_df['domain'].isna()]
    
    # Calculate statistics and create matrices
    monthly_stats = calculate_monthly_stats(merged_df)
    event_count_matrix, hours_matrix, cost_matrix = create_metric_matrices(monthly_stats)
    
    # Combine all metrics
    combined_matrix = combine_matrices(event_count_matrix, hours_matrix, cost_matrix)
    
    # Save results
    save_output_files(combined_matrix, monthly_stats, unmatched_events)

if __name__ == "__main__":
    analyze_program_events() 