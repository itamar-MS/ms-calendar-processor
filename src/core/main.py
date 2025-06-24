import pandas as pd
from pathlib import Path
import argparse
from data.parsers.calendar_parser import process_calendar_events
from reports.generators import generate_instructor_reports, duplicate_events_for_testing
from reports.handlers import CSVHandler, S3Handler, Base44SyncHandler
from dotenv import load_dotenv
from datetime import datetime

def output_events_to_csv(expanded_df, output_dir):
    """Output events to CSV files."""
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

def get_handlers(handler_names):
    """Get handler instances based on handler names."""
    handlers = []
    for name in handler_names:
        if name == 'csv':
            handlers.append(CSVHandler())
        elif name == 's3':
            handlers.append(S3Handler())
        elif name == 'base44sync':
            handlers.append(Base44SyncHandler())
        else:
            raise ValueError(f"Unknown handler: {name}")
    return handlers

def parse_args():
    parser = argparse.ArgumentParser(
        description='Process calendar events and generate reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate event list CSV files
  python run.py --event-list

  # Generate instructor reports for a specific month and save to CSV only
  python run.py --instructor-reports --month 2025-04 --handlers csv

  # Generate instructor reports for the current month
  python run.py --instructor-reports --current-month --handlers csv

  # Generate instructor reports and upload to S3 (with HubSpot updates)
  python run.py --instructor-reports --month 2025-04 --handlers s3

  # Generate instructor reports and sync with Base44
  python run.py --instructor-reports --month 2025-04 --handlers base44sync

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
    parser.add_argument('--month', type=str,
                      help='Target month for instructor reports (format: YYYY-MM)')
    parser.add_argument('--current-month', action='store_true',
                      help='Generate instructor reports for the current month')
    parser.add_argument('--handlers', nargs='+', default=['csv'],
                      help='List of handlers to use for processing reports (default: csv)')
    parser.add_argument('--duplicate-events', nargs=2, metavar=('SOURCE_EMAIL', 'TARGET_EMAIL'),
                      help='Duplicate events from source instructor to target instructor')
    
    args = parser.parse_args()
    
    if not args.event_list and not args.instructor_reports:
        parser.print_help()
        return
    
    if args.instructor_reports and not args.month and not args.current_month:
        parser.error("Either --month or --current-month is required when using --instructor-reports")
    
    if args.instructor_reports and args.month and args.current_month:
        parser.error("Cannot specify both --month and --current-month")
    
    return args

def main():
    load_dotenv()
    args = parse_args()
    
    # Get processed calendar events
    events_df = process_calendar_events()
    
    # DEBUG: Output raw events DataFrame to CSV for inspection
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    events_df.to_csv(output_dir / 'raw_events_from_db.csv', index=False)
    
    if args.duplicate_events:
        source_email, target_email = args.duplicate_events
        events_df = duplicate_events_for_testing(events_df, source_email, target_email)
    
    if args.event_list:
        print("Generating event list CSV files...")
        output_events_to_csv(events_df, Path('output'))
        print(f"CSV files generated in output directory")
    
    if args.instructor_reports:
        # Determine the target month
        if args.current_month:
            target_month = datetime.now().strftime('%Y-%m')
        else:
            target_month = args.month
            
        print(f"Generating instructor reports for {target_month}...")
        # Generate the reports
        instructor_reports = generate_instructor_reports(events_df, target_month)
        
        if instructor_reports:
            try:
                # Get the requested handlers
                handlers = get_handlers(args.handlers)
                
                # Process reports with the selected handlers
                for handler in handlers:
                    print(f"\nProcessing reports with {handler.__class__.__name__}...")
                    handler.process_reports(instructor_reports, target_month)
            except ValueError as e:
                print(str(e))
        else:
            print("No reports were generated.")

if __name__ == "__main__":
    main() 