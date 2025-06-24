import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from dateutil import rrule
import json
from pathlib import Path
from data.database.calendar_queries import get_calendar_events, get_tutoring_sessions

def parse_rrule(rrule_str):
    """Parse RRULE string and return a dict of parameters."""
    if not rrule_str:  # This handles both None and empty string
        return None
    
    # Clean the string - remove quotes and extra whitespace
    rrule_str = rrule_str.strip().strip('"')
    
    # Handle DTSTART if present
    dtstart = None
    if rrule_str.startswith('DTSTART:'):
        dtstart_line, rrule_str = rrule_str.split('\nRRULE:', 1)
        dtstart = pd.to_datetime(dtstart_line.replace('DTSTART:', ''))
    
    params = {}
    parts = rrule_str.split(';')
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            params[key] = value
        else:
            key, value = part.split('=', 1)
            params[key] = value
    
    if dtstart:
        params['DTSTART'] = dtstart
    return params

def expand_recurring_event(row):
    """Expand a recurring event into individual occurrences."""
    if not row['rrule']:  # This handles both None and empty string
        return [row]
    
    rrule_params = parse_rrule(row['rrule'])
    if not rrule_params:
        return [row]
    
    # Parse start and end times
    event_start = pd.to_datetime(row['start_time'])
    end_time = pd.to_datetime(row['end_time'])
    duration = end_time - event_start
    
    # Get recurrence parameters
    freq = rrule_params.get('FREQ', 'WEEKLY')
    interval = int(rrule_params.get('INTERVAL', 1))
    byday = rrule_params.get('BYDAY', None)
    count = rrule_params.get('COUNT', None)
    
    # Convert frequency to rrule constant
    freq_map = {
        'YEARLY': rrule.YEARLY,
        'MONTHLY': rrule.MONTHLY,
        'WEEKLY': rrule.WEEKLY,
        'DAILY': rrule.DAILY,
        'HOURLY': rrule.HOURLY,
        'MINUTELY': rrule.MINUTELY,
        'SECONDLY': rrule.SECONDLY
    }
    
    # Handle BYDAY parameter
    if byday:
        byday = byday.split(',')
        byday = [getattr(rrule, day[:2].upper()) for day in byday]
    
    # Get end date from rrule_until or use May 31st, 2025 as default
    # Ensure timezone awareness matches event_start
    default_until = pd.to_datetime('2025-05-31T23:59:59Z')  # UTC
    until = default_until  # Start with default
    
    # If there's a specific rrule_until date in the row, use that instead of the default
    if row['rrule_until']:
        try:
            until = pd.to_datetime(row['rrule_until'])
            if pd.isna(until):  # If conversion resulted in NaT, use default
                until = default_until
        except:
            until = default_until
    
    # Always convert to UTC for rrule
    if event_start.tzinfo is not None:
        # Convert event_start to UTC
        event_start = event_start.tz_convert('UTC')
        
        # Convert until to UTC
        if until.tzinfo is None:
            until = until.tz_localize('UTC')
        else:
            until = until.tz_convert('UTC')
    else:
        # If event_start is naive, make until naive too
        if until.tzinfo is not None:
            until = until.tz_localize(None)
    
    # Generate dates
    rrule_args = {
        'freq': freq_map.get(freq, rrule.WEEKLY),
        'interval': interval,
        'dtstart': event_start,  # Use the event's start time, not DTSTART from RRULE
        'until': until
    }

    # Add BYDAY if present
    if byday:
        rrule_args['byweekday'] = byday

    # Handle COUNT parameter only if it would end before the until date
    if count:
        # Calculate when the count would end
        count_dates = list(rrule.rrule(
            freq=rrule_args['freq'],
            interval=interval,
            dtstart=event_start,
            count=int(count)
        ))
        if count_dates:
            count_end = count_dates[-1]
            # Use the earlier of count_end and until
            rrule_args['until'] = min(count_end, until)

    dates = list(rrule.rrule(**rrule_args))
    
    # Manually enforce COUNT if specified
    if count:
        dates = dates[:int(count)]
    
    # Handle exclusions
    ex_dates = []
    rrule_ex_date = row['rrule_ex_date']
    if rrule_ex_date:  # This will handle both None and empty list
        ex_dates = [pd.to_datetime(d).date() for d in rrule_ex_date]
    
    # Create expanded events
    expanded_events = []
    for date in dates:
        # Compare only the date parts for exclusion
        if date.date() not in ex_dates:
            event = row.copy()
            event['start_time'] = date
            event['end_time'] = date + duration
            expanded_events.append(event)
    
    return expanded_events

def is_primary_instructor_event(row):
    """Determine if this is the primary instructor's event."""
    # Check if instructor_calendar_id matches the event id
    if row['instructor_calendar_id'] != row['id']:
        return False
    
    # Check if description indicates it's the instructor's calendar
    description = str(row['description']).lower()
    return any(phrase in description for phrase in [
        'personal calendar for ms employee',
        'personal calendar for user',
        'personal calendar for masterschool employee'
    ])

def get_fullcalendar_id(row):
    """Generate a FullCalendar-compatible event ID."""
    # Base event ID
    event_id = row['id']
    
    # For recurring events, append the date to create a unique occurrence ID
    if row['rrule']:
        start_time = pd.to_datetime(row['start_time'])
        # Format: baseEventId_YYYYMMDD (FullCalendar's pattern)
        return f"{event_id}_{start_time.strftime('%Y%m%d')}"
    
    return event_id

def get_event_source_id(row):
    """Get the calendar source ID (instructor calendar)."""
    return row['instructor_calendar_id']

def normalize_title(title):
    """Normalize event title by removing extra spaces and handling NaN values."""
    if not title:  # This handles both None and empty string
        return 'Untitled Event'
    return ' '.join(str(title).split())

def extract_series_and_topic(title):
    """Extract series name and topic from event title."""
    title = normalize_title(title)
    parts = title.split(' - ', 1)
    series = parts[0] if parts else ''
    topic = parts[1] if len(parts) > 1 else ''
    return series, topic

def get_time_slot_key(start_time):
    """Generate a consistent key for the time slot."""
    dt = pd.to_datetime(start_time)
    return f"{dt.hour:02d}:{dt.minute:02d}"

def get_recurrence_key(row):
    """Generate a key for the event's recurrence pattern."""
    if not row['rrule']:  # This handles both None and empty string
        return 'single'
        
    rrule_params = parse_rrule(row['rrule'])
    if not rrule_params:
        return 'single'
        
    # Extract key recurrence information
    freq = rrule_params.get('FREQ', '')
    interval = rrule_params.get('INTERVAL', '1')
    byday = rrule_params.get('BYDAY', '')
    
    return f"{freq}_{interval}_{byday}"

def get_sequence_position(row):
    """Determine the position of an event in its sequence based on start time."""
    if not row['rrule']:  # This handles both None and empty string
        return 0
        
    rrule_params = parse_rrule(row['rrule'])
    if not rrule_params:
        return 0
    
    # Get the first occurrence date
    first_occurrence = pd.to_datetime(row['start_time'])
    
    # For recurring events, calculate weeks since first occurrence
    # This gives us the position in the sequence
    current_date = pd.to_datetime(row['start_time'])
    weeks_diff = (current_date - first_occurrence).days // 7
    
    return weeks_diff

def get_event_key(row):
    """
    Generate a unique key for event deduplication based on:
    1. Series name (e.g., "Proficient Python")
    2. Topic (e.g., "Nested Structures")
    3. Time slot (e.g., "09:30")
    4. Start date
    5. Recurrence pattern
    """
    # Handle title first to avoid NaN issues
    title = row.get('title', '')
    if not title:  # This handles both None and empty string
        title = 'Untitled Event'
    
    series, topic = extract_series_and_topic(title)
    start_time = pd.to_datetime(row['start_time'])
    time_slot = get_time_slot_key(start_time)
    
    # Extract recurrence information
    rrule = row.get('rrule', '')
    excluded_dates = row.get('rrule_ex_date', [])
    if isinstance(excluded_dates, str):
        try:
            excluded_dates = json.loads(excluded_dates)
        except:
            excluded_dates = []
    
    # Create a comprehensive key that identifies unique content
    key_parts = [
        series,
        topic,
        time_slot,
        start_time.strftime('%Y-%m-%d'),
        str(rrule),
        str(sorted(excluded_dates)) if excluded_dates else ''
    ]
    
    return '|'.join(filter(None, key_parts))

def process_calendar_events():
    """Process calendar events and return a DataFrame with the results."""
    # Read the calendar events from the database
    df = get_calendar_events()
    
    # Filter out deleted events
    df = df[df['deleted_at'].isna()]
    
    # Process recurring events
    recurring_events = df[df['recurring_group_id'].notna()].copy()
    single_events = df[df['recurring_group_id'].isna()].copy()
    
    # Expand recurring events
    expanded_events = []
    for _, group in recurring_events.groupby('recurring_group_id'):
        for _, row in group.iterrows():
            expanded = expand_recurring_event(row)
            # Convert each event to a clean dictionary
            for event in expanded:
                clean_event = {}
                for key, value in event.items():
                    if value is None or (isinstance(value, (list, str)) and not value):  # Handle None, empty lists, and empty strings
                        clean_event[key] = None
                    else:
                        clean_event[key] = value
                expanded_events.append(clean_event)
    
    # Add single events
    for _, row in single_events.iterrows():
        clean_event = {}
        for key, value in row.items():
            if value is None or (isinstance(value, (list, str)) and not value):  # Handle None, empty lists, and empty strings
                clean_event[key] = None
            else:
                clean_event[key] = value
        expanded_events.append(clean_event)
    
    # Convert to DataFrame
    expanded_df = pd.DataFrame(expanded_events)
    
    # Convert timestamps to datetime
    expanded_df['start_time'] = pd.to_datetime(expanded_df['start_time'])
    expanded_df['end_time'] = pd.to_datetime(expanded_df['end_time'])
    
    # Calculate duration in hours
    expanded_df['duration_hours'] = (expanded_df['end_time'] - expanded_df['start_time']).dt.total_seconds() / 3600
    
    return expanded_df

def process_tutoring_sessions():
    """Process tutoring sessions and return a DataFrame with the results."""
    # Read the tutoring sessions from the database
    df = get_tutoring_sessions()
    
    # Filter out deleted events
    df = df[df['deleted_at'].isna()]
    
    # Process recurring events
    recurring_events = df[df['recurring_group_id'].notna()].copy()
    single_events = df[df['recurring_group_id'].isna()].copy()
    
    # Expand recurring events
    expanded_events = []
    for _, group in recurring_events.groupby('recurring_group_id'):
        for _, row in group.iterrows():
            expanded = expand_recurring_event(row)
            # Convert each event to a clean dictionary
            for event in expanded:
                clean_event = {}
                for key, value in event.items():
                    if value is None or (isinstance(value, (list, str)) and not value):  # Handle None, empty lists, and empty strings
                        clean_event[key] = None
                    else:
                        clean_event[key] = value
                expanded_events.append(clean_event)
    
    # Add single events
    for _, row in single_events.iterrows():
        clean_event = {}
        for key, value in row.items():
            if value is None or (isinstance(value, (list, str)) and not value):  # Handle None, empty lists, and empty strings
                clean_event[key] = None
            else:
                clean_event[key] = value
        expanded_events.append(clean_event)
    
    # Convert to DataFrame
    expanded_df = pd.DataFrame(expanded_events)
    
    # Convert timestamps to datetime
    expanded_df['start_time'] = pd.to_datetime(expanded_df['start_time'])
    expanded_df['end_time'] = pd.to_datetime(expanded_df['end_time'])
    
    # Calculate duration in hours
    expanded_df['duration_hours'] = (expanded_df['end_time'] - expanded_df['start_time']).dt.total_seconds() / 3600
    
    return expanded_df 