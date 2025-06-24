# db/calendar_queries.py
from data.database.postgres_handler import PostgresHandler

def get_calendar_events():
    """Return a DataFrame of calendar events from the appropriate database."""
    # For now, hardcode the database name. You can later make this configurable or dynamic.
    db_name = 'CampusDB'
    db_handler = PostgresHandler.for_db(db_name)
    query = """
    select ms_event.id as ms_event_id,
      users.email,
      users.first_name || ' ' || users.last_name as name,
      ms_event.title,
      ms_event.start_time,
      ms_event.end_time,
      ms_event.deleted_at, 
      ms_event.recurring_group_id,
      ms_event.rrule,
      ms_event.rrule_tzid,
      ms_event.rrule_until,
      ms_event.rrule_ex_date
    from ms_event
    join ms_calendar on ms_calendar.id = ms_event.instructor_calendar_id
    join user_to_ms_calendar on user_to_ms_calendar.ms_calendar_id = ms_calendar.id
    join users on users.client_id = user_to_ms_calendar.user_client_id
    where instructor_calendar_id is not null
    order by start_time desc;
    """
    return db_handler.query_to_df(query)

def get_tutoring_sessions():
    """Return a DataFrame of tutoring sessions from the appropriate database."""
    # For now, hardcode the database name. You can later make this configurable or dynamic.
    db_name = 'CampusDB'
    db_handler = PostgresHandler.for_db(db_name)
    query = """
    SELECT ms_event.id as ms_event_id,
      users.email,
      users.first_name || ' ' || users.last_name as name,
      ms_event.title,
      ms_event.start_time,
      ms_event.end_time,
      ms_event.deleted_at,
      ms_event.recurring_group_id,
      ms_event.rrule,
      ms_event.rrule_tzid,
      ms_event.rrule_until,
      ms_event.rrule_ex_date
    FROM ms_event
    JOIN ms_calendar_to_event ON ms_calendar_to_event.ms_event_id = ms_event.id
    JOIN ms_calendar ON ms_calendar.id = ms_calendar_to_event.ms_calendar_id
    JOIN user_to_ms_calendar ON user_to_ms_calendar.ms_calendar_id = ms_calendar.id
    JOIN users ON users.client_id = user_to_ms_calendar.user_client_id
    JOIN user_to_role ON users.id = user_to_role.user_id
    WHERE ms_event.type = 'tutoring-session'
      AND user_to_role.role = 'tutor'
    ORDER BY start_time DESC;
    """
    return db_handler.query_to_df(query)

if __name__ == '__main__':
    # Test function to call get_calendar_events and print the results
    df = get_calendar_events()
    print(df)

# Add more query functions as needed for other calendar-related queries 