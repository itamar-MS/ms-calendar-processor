import pandas as pd
from pathlib import Path
import argparse
from data.parsers.calendar_parser import process_calendar_events, process_tutoring_sessions
from reports.generators import generate_instructor_reports, generate_tutor_reports, duplicate_events_for_testing
from reports.handlers import CSVHandler, S3Handler, Base44SyncHandler
from dotenv import load_dotenv
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

def output_events_to_csv(expanded_df, output_dir, activity_type="instructor"):
    """Output events to CSV files."""
    # Create events list CSV
    events_list = expanded_df[['name', 'title', 'start_time', 'end_time', 'duration_hours', 'ms_event_id', 'email']].copy()
    
    # Sort by instructor/tutor name first, then by start time
    events_list = events_list.sort_values(['name', 'start_time'])
    filename = f'{activity_type}_events_list.csv'
    events_list.to_csv(output_dir / filename, index=False)
    
    # Create monthly instructor/tutor hours CSV
    monthly_hours = expanded_df.copy()
    monthly_hours['month'] = monthly_hours['start_time'].dt.to_period('M')
    
    monthly_stats = monthly_hours.groupby(['name', 'month']).agg({
        'duration_hours': 'sum',
        'title': 'count'
    }).reset_index()
    
    monthly_stats.columns = ['name', 'month', 'duration_hours', 'session_count']
    monthly_stats['month'] = monthly_stats['month'].astype(str)
    filename = f'monthly_{activity_type}_hours.csv'
    monthly_stats.to_csv(output_dir / filename, index=False)

def get_handlers(handler_names, activity_type="instruction"):
    """Get handler instances based on handler names."""
    handlers = []
    for name in handler_names:
        if name == 'csv':
            handlers.append(CSVHandler())
        elif name == 's3':
            handlers.append(S3Handler())
        elif name == 'base44sync':
            handlers.append(Base44SyncHandler(activity_type=activity_type))
        else:
            raise ValueError(f"Unknown handler: {name}")
    return handlers

def generate_month_range(start_month="2025-01"):
    """Generate a list of months from start_month to current month."""
    start_date = datetime.strptime(start_month, "%Y-%m")
    current_date = datetime.now()
    
    months = []
    current_month = start_date
    
    while current_month <= current_date:
        months.append(current_month.strftime("%Y-%m"))
        current_month = current_month + relativedelta(months=1)
    
    return months

def process_reports_for_month(target_month, activity_type, args):
    """Process reports for a specific month."""
    print(f"\nProcessing {activity_type} reports for {target_month}...")
    
    if args.instructor_reports:
        # Load instructor sessions data
        instructor_events_df = process_calendar_events()
        print("Processing instructor sessions...")
        
        # Generate instructor reports
        instructor_reports = generate_instructor_reports(instructor_events_df, target_month)
        
        if instructor_reports:
            try:
                # Get the requested handlers
                handlers = get_handlers(args.handlers, activity_type="instruction")
                
                # Process reports with the selected handlers
                for handler in handlers:
                    print(f"Processing instructor reports with {handler.__class__.__name__}...")
                    handler.process_reports(instructor_reports, target_month)
            except ValueError as e:
                print(str(e))
        else:
            print(f"No instructor reports generated for {target_month}")
    
    if args.tutor_reports:
        # Load tutoring sessions data
        tutor_events_df = process_tutoring_sessions()
        print("Processing tutoring sessions...")
        
        # Generate tutor reports
        tutor_reports = generate_tutor_reports(tutor_events_df, target_month)
        
        if tutor_reports:
            try:
                # Get the requested handlers
                handlers = get_handlers(args.handlers, activity_type="tutoring")
                
                # Process reports with the selected handlers
                for handler in handlers:
                    print(f"Processing tutor reports with {handler.__class__.__name__}...")
                    handler.process_reports(tutor_reports, target_month)
            except ValueError as e:
                print(str(e))
        else:
            print(f"No tutor reports generated for {target_month}")

def parse_args():
    parser = argparse.ArgumentParser(
        description='Process calendar events and generate reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate event list CSV files for instructors
  python run.py --event-list

  # Generate event list CSV files for tutoring sessions
  python run.py --event-list --tutoring-sessions

  # Generate instructor reports for a specific month and save to CSV only
  python run.py --instructor-reports --month 2025-04 --handlers csv

  # Generate tutor reports for a specific month and save to CSV only
  python run.py --tutor-reports --month 2025-04 --handlers csv

  # Generate instructor reports for the current month
  python run.py --instructor-reports --current-month --handlers csv

  # Generate instructor reports and upload to S3 (with HubSpot updates)
  python run.py --instructor-reports --month 2025-04 --handlers s3

  # Generate instructor reports and sync with Base44
  python run.py --instructor-reports --month 2025-04 --handlers base44sync

  # Generate tutor reports and sync with Base44
  python run.py --tutor-reports --month 2025-04 --handlers base44sync

  # Update all months from 2025-01 to current month for both instructor and tutor reports
  python run.py --update-all-months --instructor-reports --tutor-reports --handlers csv base44sync

  # Update all months for instructor reports only
  python run.py --update-all-months --instructor-reports --handlers base44sync

  # Generate instructor reports and use multiple handlers
  python run.py --instructor-reports --month 2025-04 --handlers csv s3 base44sync

  # Generate both event list and instructor reports with all handlers
  python run.py --event-list --instructor-reports --month 2025-04 --handlers csv s3 base44sync

Available Handlers:
  csv        - Save reports to CSV files in the output directory
  s3         - Upload reports to S3 and update HubSpot contacts
  base44sync - Sync reports with Base44 time tracking system
        """
    )
    
    parser.add_argument('--event-list', action='store_true',
                      help='Generate event list CSV files')
    parser.add_argument('--instructor-reports', action='store_true',
                      help='Generate instructor reports')
    parser.add_argument('--tutor-reports', action='store_true',
                      help='Generate tutor reports')
    parser.add_argument('--tutoring-sessions', action='store_true',
                      help='Process tutoring sessions instead of instructor sessions')
    parser.add_argument('--month', type=str,
                      help='Target month for reports (format: YYYY-MM)')
    parser.add_argument('--current-month', action='store_true',
                      help='Generate reports for the current month')
    parser.add_argument('--update-all-months', action='store_true',
                      help='Update all months from 2025-01 to current month')
    parser.add_argument('--handlers', nargs='+', default=['csv'],
                      help='List of handlers to use for processing reports (default: csv)')
    parser.add_argument('--duplicate-events', nargs=2, metavar=('SOURCE_EMAIL', 'TARGET_EMAIL'),
                      help='Duplicate events from source instructor to target instructor')
    
    args = parser.parse_args()
    
    if not args.event_list and not args.instructor_reports and not args.tutor_reports:
        parser.print_help()
        return
    
    if args.update_all_months:
        # When using --update-all-months, we don't need --month or --current-month
        if args.month or args.current_month:
            parser.error("Cannot use --month or --current-month with --update-all-months")
    else:
        # When not using --update-all-months, we need either --month or --current-month for reports
        if (args.instructor_reports or args.tutor_reports) and not args.month and not args.current_month:
            parser.error("Either --month or --current-month is required when using --instructor-reports or --tutor-reports")
        
        if (args.instructor_reports or args.tutor_reports) and args.month and args.current_month:
            parser.error("Cannot specify both --month and --current-month")
    
    return args

def main():
    load_dotenv()
    args = parse_args()
    
    # Create output directory
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    if args.duplicate_events:
        source_email, target_email = args.duplicate_events
        # For duplicate events, we need to load data first
        if args.tutoring_sessions or args.tutor_reports:
            events_df = process_tutoring_sessions()
            print("Processing tutoring sessions...")
        else:
            events_df = process_calendar_events()
            print("Processing instructor sessions...")
        events_df = duplicate_events_for_testing(events_df, source_email, target_email)
    
    if args.event_list:
        # Load appropriate data for event list
        if args.tutoring_sessions or args.tutor_reports:
            activity_type = "tutoring"
            events_df = process_tutoring_sessions()
            print("Processing tutoring sessions...")
        else:
            activity_type = "instruction"
            events_df = process_calendar_events()
            print("Processing instructor sessions...")
        
        # DEBUG: Output raw events DataFrame to CSV for inspection
        filename = f'raw_{activity_type}_events_from_db.csv'
        events_df.to_csv(output_dir / filename, index=False)
        
        print(f"Generating {activity_type} event list CSV files...")
        output_events_to_csv(events_df, Path('output'), activity_type)
        print(f"CSV files generated in output directory")
    
    if args.update_all_months:
        # Process all months from 2025-01 to current month
        months = generate_month_range("2025-01")
        print(f"Processing {len(months)} months: {', '.join(months)}")
        
        for target_month in months:
            process_reports_for_month(target_month, "all", args)
        
        print(f"\nCompleted processing all months from 2025-01 to current month")
    
    elif args.instructor_reports or args.tutor_reports:
        # Determine the target month
        if args.current_month:
            target_month = datetime.now().strftime('%Y-%m')
        else:
            target_month = args.month
            
        process_reports_for_month(target_month, "all", args)

if __name__ == "__main__":
    main() 