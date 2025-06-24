import pandas as pd
from pathlib import Path
from data.parsers.calendar_parser import process_calendar_events

def main():
    # Create output directory if it doesn't exist
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    # Get processed calendar events
    expanded_df = process_calendar_events()
    
    # Create events list CSV
    events_list = expanded_df[['name', 'title', 'start_time', 'end_time', 'duration_hours', 'ms_event_id', 'email']].copy()
    
    # Sort by instructor name first, then by start time
    events_list = events_list.sort_values(['name', 'start_time'])
    events_list.to_csv(output_dir / 'events_list.csv', index=False)
    
    # Create monthly instructor hours CSV
    monthly_hours = expanded_df.copy()
    monthly_hours['month'] = monthly_hours['start_time'].dt.to_period('M')
    
    monthly_stats = monthly_hours.groupby(['name', 'month']).agg({
        'duration_hours': 'sum',
        'title': 'count'
    }).reset_index()
    
    monthly_stats.columns = ['name', 'month', 'duration_hours', 'session_count']
    monthly_stats['month'] = monthly_stats['month'].astype(str)
    monthly_stats.to_csv(output_dir / 'monthly_instructor_hours.csv', index=False)

if __name__ == '__main__':
    main() 