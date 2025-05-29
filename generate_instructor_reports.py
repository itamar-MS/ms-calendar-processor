import pandas as pd
import os
from pathlib import Path
from s3_utils import create_s3_bucket, upload_file_to_s3, get_s3_url, generate_unique_filename
from hubspot_utils import get_hubspot_client, search_contact_by_email, update_contact_property, save_not_found_contacts
from dotenv import load_dotenv
import argparse
from report_generators import generate_instructor_reports
from report_handlers import CSVHandler, S3Handler

# Load environment variables
load_dotenv()

# Constants from environment variables
INPUT_FILE = 'output/events_list.csv'
OUTPUT_DIR = 'output/instructor_reports'
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
HUBSPOT_PROPERTY_NAME = 'monthly_report'

# Column name mappings
COLUMN_MAPPINGS = {
    'name': 'Instructor Name',
    'title': 'Session Title',
    'start_time': 'Start Time',
    'end_time': 'End Time',
    'duration_hours': 'Duration (Hours)'
}

def ensure_output_directory():
    """Create the output directory if it doesn't exist."""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

def read_events_data():
    """Read the events data from CSV."""
    return pd.read_csv(INPUT_FILE)

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
    """Generate separate CSV files for each instructor for the target month."""
    # Clean instructor names
    events_df['name'] = events_df['name'].apply(clean_instructor_name)
    
    # Convert start_time to datetime and filter for target month
    events_df['start_time'] = pd.to_datetime(events_df['start_time'], format='ISO8601')
    target_month_events = events_df[events_df['start_time'].dt.strftime('%Y-%m') == target_month]
    
    if target_month_events.empty:
        print(f"No events found for {target_month}")
        return
    
    # Create S3 bucket if it doesn't exist
    create_s3_bucket(S3_BUCKET_NAME, region=AWS_REGION)
    
    # Initialize HubSpot client
    hubspot_client = get_hubspot_client()
    
    # Track not found contacts
    not_found_contacts = []
    
    # Group events by instructor
    for instructor, instructor_events in target_month_events.groupby('name'):
        # Get the email for this instructor
        email = instructor_events['email'].iloc[0] if 'email' in instructor_events.columns else 'no_email'
        
        # Create local filename (without email)
        local_filename = f"{instructor.replace(' ', '_')}_{target_month}_events.csv"
        output_path = os.path.join(OUTPUT_DIR, local_filename)
        
        # Sort events by start time
        instructor_events = instructor_events.sort_values('start_time')
        
        # Format the report
        formatted_report = format_instructor_report(instructor_events)
        
        # Save to CSV
        formatted_report.to_csv(output_path, index=False)
        
        # Generate S3 filename with name, date, and UUID
        s3_filename = generate_unique_filename(instructor, target_month, local_filename)
        s3_key = f"{target_month}/{s3_filename}"
        
        # Upload to S3
        if upload_file_to_s3(output_path, S3_BUCKET_NAME, s3_key):
            s3_url = get_s3_url(S3_BUCKET_NAME, s3_key)
            print(f"\nGenerated report for {instructor} ({email}) for {target_month}")
            print(f"Local file: {local_filename}")
            print(f"S3 file: {s3_filename}")
            print(f"Public URL: {s3_url}")
            
            # Search for contact in HubSpot
            contact_id = search_contact_by_email(hubspot_client, email)
            if contact_id:
                # Update the contact's property
                if update_contact_property(hubspot_client, contact_id, HUBSPOT_PROPERTY_NAME, s3_url):
                    print(f"Updated HubSpot contact {contact_id} with S3 URL")
                else:
                    print(f"Failed to update HubSpot contact {contact_id}")
            else:
                print(f"Contact not found in HubSpot for email: {email}")
                not_found_contacts.append({
                    'email': email,
                    'name': instructor,
                    's3_url': s3_url
                })
    
    # Save not found contacts to CSV
    save_not_found_contacts(not_found_contacts, OUTPUT_DIR)

def main(expanded_df=None, target_month=None):
    """Main function to generate instructor reports."""
    # If called directly (not from main.py), get parameters from command line
    if expanded_df is None or target_month is None:
        parser = argparse.ArgumentParser(description='Generate instructor reports for a specific month')
        parser.add_argument('--month', type=str, required=True,
                          help='Target month for instructor reports (format: YYYY-MM)')
        args = parser.parse_args()
        target_month = args.month
        expanded_df = read_events_data()
    
    print(f"Starting instructor report generation for {target_month}...")
    
    # Generate the reports
    instructor_reports = generate_instructor_reports(expanded_df, target_month)
    
    if not instructor_reports:
        print("No reports were generated.")
        return
    
    # Process reports with different handlers
    handlers = [
        CSVHandler(),
        S3Handler()
    ]
    
    for handler in handlers:
        handler.process_reports(instructor_reports, target_month)

if __name__ == "__main__":
    main() 