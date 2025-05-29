import pandas as pd
from pathlib import Path
import argparse
from calendar_utils.parse_raw_events import process_calendar_events
from report_generators import generate_instructor_reports
from report_handlers import CSVHandler, S3Handler

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
    """Get the requested handlers based on their names."""
    available_handlers = {
        'csv': CSVHandler,
        's3': S3Handler
    }
    
    handlers = []
    for name in handler_names:
        if name not in available_handlers:
            raise ValueError(f"Unknown handler: {name}. Available handlers: {', '.join(available_handlers.keys())}")
        handlers.append(available_handlers[name]())
    
    return handlers

def main():
    parser = argparse.ArgumentParser(
        description='Process calendar events and generate reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate event list CSV files
  python main.py --event-list

  # Generate instructor reports for a specific month and save to CSV only
  python main.py --instructor-reports --month 2025-04 --handlers csv

  # Generate instructor reports and upload to S3 (with HubSpot updates)
  python main.py --instructor-reports --month 2025-04 --handlers s3

  # Generate instructor reports and use both CSV and S3 handlers
  python main.py --instructor-reports --month 2025-04 --handlers csv s3

  # Generate both event list and instructor reports with all handlers
  python main.py --event-list --instructor-reports --month 2025-04 --handlers csv s3

Available Handlers:
  csv - Save reports to CSV files in the output directory
  s3  - Upload reports to S3 and update HubSpot contacts
        """
    )
    
    parser.add_argument('--event-list', action='store_true',
                      help='Generate event list CSV files')
    parser.add_argument('--instructor-reports', action='store_true',
                      help='Generate instructor reports')
    parser.add_argument('--month', type=str,
                      help='Target month for instructor reports (format: YYYY-MM)')
    parser.add_argument('--handlers', nargs='+', default=['csv', 's3'],
                      help='List of handlers to use for processing reports (default: csv s3)')
    
    args = parser.parse_args()
    
    if not args.event_list and not args.instructor_reports:
        parser.print_help()
        return
    
    if args.instructor_reports and not args.month:
        parser.error("--month is required when using --instructor-reports")
    
    # Create output directory if it doesn't exist
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    # Get processed calendar events
    expanded_df = process_calendar_events()
    
    if args.event_list:
        print("Generating event list CSV files...")
        output_events_to_csv(expanded_df, output_dir)
        print(f"CSV files generated in {output_dir}")
    
    if args.instructor_reports:
        print(f"Generating instructor reports for {args.month}...")
        # Generate the reports
        instructor_reports = generate_instructor_reports(expanded_df, args.month)
        
        if instructor_reports:
            try:
                # Get the requested handlers
                handlers = get_handlers(args.handlers)
                
                # Process reports with the selected handlers
                for handler in handlers:
                    print(f"\nProcessing reports with {handler.__class__.__name__}...")
                    handler.process_reports(instructor_reports, args.month)
            except ValueError as e:
                parser.error(str(e))
        else:
            print("No reports were generated.")

if __name__ == '__main__':
    main() 