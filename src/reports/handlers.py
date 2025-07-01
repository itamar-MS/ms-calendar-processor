import os
import tempfile
from pathlib import Path
from services.s3_service import create_s3_bucket, upload_file_to_s3, get_s3_url, generate_unique_filename
from services.hubspot_service import get_hubspot_client, search_contact_by_email, update_contact_property, save_not_found_contacts
from dotenv import load_dotenv
from services.base44_service import Base44API
from datetime import datetime
import pandas as pd
from core.config import Config

# Load environment variables
load_dotenv()

class BaseHandler:
    """Base class for report handlers."""
    def process_reports(self, faculty_reports, target_month):
        """Process the reports. To be implemented by subclasses."""
        raise NotImplementedError

class CSVHandler(BaseHandler):
    """Handler for saving reports to CSV files."""
    def __init__(self, output_dir='output/faculty_reports'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_reports(self, faculty_reports, target_month):
        """Save each faculty member's report to a CSV file."""
        for faculty_member, report_data in faculty_reports.items():
            local_filename = f"{faculty_member.replace(' ', '_')}_{target_month}_faculty_report.csv"
            output_path = self.output_dir / local_filename
            report_data['report'].to_csv(output_path, index=False)
            print(f"Saved faculty report for {faculty_member} to {output_path}")

class S3Handler(BaseHandler):
    """Handler for uploading reports to S3 and updating HubSpot."""
    def __init__(self, bucket_name=None, region=None):
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
        self.region = region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.hubspot_property = Config.HUBSPOT_PROPERTY
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable is not set")
        
        # Create S3 bucket if it doesn't exist
        create_s3_bucket(self.bucket_name, region=self.region)
        
        # Initialize HubSpot client
        self.hubspot_client = get_hubspot_client()
    
    def process_reports(self, faculty_reports, target_month):
        """Upload faculty reports to S3 and update HubSpot contacts."""
        not_found_contacts = []
        
        for faculty_member, report_data in faculty_reports.items():
            email = report_data['email']
            report = report_data['report']
            
            # Generate filenames
            local_filename = f"{faculty_member.replace(' ', '_')}_{target_month}_faculty_report.csv"
            s3_filename = generate_unique_filename(faculty_member, target_month, local_filename)
            s3_key = f"{target_month}/{s3_filename}"
            
            # Use tempfile to create a temporary file that will be automatically cleaned up
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=True) as temp_file:
                # Save report to temporary file
                report.to_csv(temp_file.name, index=False)
                
                # Upload to S3
                if upload_file_to_s3(temp_file.name, self.bucket_name, s3_key):
                    s3_url = get_s3_url(self.bucket_name, s3_key)
                    print(f"\nUploaded faculty report for {faculty_member} ({email}) to S3")
                    print(f"S3 file: {s3_filename}")
                    print(f"Public URL: {s3_url}")
                    
                    # Update HubSpot
                    contact_id = search_contact_by_email(self.hubspot_client, email)
                    if contact_id:
                        if update_contact_property(self.hubspot_client, contact_id, self.hubspot_property, s3_url):
                            print(f"Updated HubSpot contact {contact_id} with S3 URL")
                        else:
                            print(f"Failed to update HubSpot contact {contact_id}")
                    else:
                        print(f"Contact not found in HubSpot for email: {email}")
                        not_found_contacts.append({
                            'email': email,
                            'name': faculty_member,
                            's3_url': s3_url
                        })
        
        # Save not found contacts
        if not_found_contacts:
            save_not_found_contacts(not_found_contacts, 'output/faculty_reports')

class Base44SyncHandler(BaseHandler):
    """Handler for syncing reports with Base44."""
    def __init__(self, activity_type="instruction"):
        self.api = Base44API()
        self.activity_type = activity_type
        
    def _prepare_base44_record(self, row: pd.Series, instructor_email: str) -> dict:
        """Convert a report row to a Base44 record format."""
        # Extract date from Start Time (format: YYYY-MM-DD HH:MM)
        start_date = pd.to_datetime(row['Start Time']).date()
        
        return {
            "faculty_email": instructor_email,
            "date": start_date.strftime('%Y-%m-%d'),
            "month": start_date.strftime('%Y-%m'),
            "activity_type": self.activity_type,
            "hours": float(row['Duration (Hours)']),
            "description": row['Session Title'],
            "course_name": ""  # We don't have course name in the report
        }
    
    def _records_match(self, base44_record: dict, report_record: dict) -> bool:
        """Compare if two records match in relevant fields."""
        relevant_fields = ['faculty_email', 'date', 'hours', 'description', 'course_name']
        return all(base44_record[field] == report_record[field] for field in relevant_fields)
    
    def process_reports(self, faculty_reports, target_month):
        """Sync reports with Base44."""
        # Fetch existing records from Base44
        existing_records = self.api.fetch_time_entries(month=target_month, activity_type=self.activity_type)
        
        # Prepare new records from reports
        new_records = []
        for faculty_member, report_data in faculty_reports.items():
            email = report_data['email']
            report = report_data['report']
            
            # Skip the total row
            report = report[report['Faculty Name'] != 'Total']
            
            # Filter by activity type if the report contains activity type column
            if 'Activity Type' in report.columns:
                # Filter to only include rows matching this handler's activity type
                filtered_report = report[report['Activity Type'] == self.activity_type]
            else:
                # If no activity type column, use all rows (backward compatibility)
                filtered_report = report
            
            # Convert each row to Base44 format
            for _, row in filtered_report.iterrows():
                new_records.append(self._prepare_base44_record(row, email))
        
        # Find records to delete (in Base44 but not in reports)
        records_to_delete = []
        for base44_record in existing_records:
            should_delete = True
            for report_record in new_records:
                if self._records_match(base44_record, report_record):
                    should_delete = False
                    break
            if should_delete:
                records_to_delete.append(base44_record['id'])
        
        # Find records to add (in reports but not in Base44)
        records_to_add = []
        for report_record in new_records:
            should_add = True
            for base44_record in existing_records:
                if self._records_match(base44_record, report_record):
                    should_add = False
                    break
            if should_add:
                records_to_add.append(report_record)
        
        # Perform sync operations
        if records_to_delete:
            print(f"Deleting {len(records_to_delete)} records from Base44 for {self.activity_type}")
            self.api.bulk_delete_time_entries(records_to_delete)
        
        if records_to_add:
            print(f"Adding {len(records_to_add)} new records to Base44 for {self.activity_type}")
            self.api.bulk_add_time_entries(records_to_add)
        
        print(f"Sync completed for {target_month} - {self.activity_type}")
        print(f"Records deleted: {len(records_to_delete)}")
        print(f"Records added: {len(records_to_add)}") 