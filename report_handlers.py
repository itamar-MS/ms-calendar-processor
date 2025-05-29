import os
import tempfile
from pathlib import Path
from s3_utils import create_s3_bucket, upload_file_to_s3, get_s3_url, generate_unique_filename
from hubspot_utils import get_hubspot_client, search_contact_by_email, update_contact_property, save_not_found_contacts
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BaseHandler:
    """Base class for report handlers."""
    def process_reports(self, instructor_reports, target_month):
        """Process the reports. To be implemented by subclasses."""
        raise NotImplementedError

class CSVHandler(BaseHandler):
    """Handler for saving reports to CSV files."""
    def __init__(self, output_dir='output/instructor_reports'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_reports(self, instructor_reports, target_month):
        """Save each instructor's report to a CSV file."""
        for instructor, report_data in instructor_reports.items():
            local_filename = f"{instructor.replace(' ', '_')}_{target_month}_events.csv"
            output_path = self.output_dir / local_filename
            report_data['report'].to_csv(output_path, index=False)
            print(f"Saved report for {instructor} to {output_path}")

class S3Handler(BaseHandler):
    """Handler for uploading reports to S3 and updating HubSpot."""
    def __init__(self, bucket_name=None, region=None):
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
        self.region = region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.hubspot_property = 'monthly_report'
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable is not set")
        
        # Create S3 bucket if it doesn't exist
        create_s3_bucket(self.bucket_name, region=self.region)
        
        # Initialize HubSpot client
        self.hubspot_client = get_hubspot_client()
    
    def process_reports(self, instructor_reports, target_month):
        """Upload reports to S3 and update HubSpot contacts."""
        not_found_contacts = []
        
        for instructor, report_data in instructor_reports.items():
            email = report_data['email']
            report = report_data['report']
            
            # Generate filenames
            local_filename = f"{instructor.replace(' ', '_')}_{target_month}_events.csv"
            s3_filename = generate_unique_filename(instructor, target_month, local_filename)
            s3_key = f"{target_month}/{s3_filename}"
            
            # Use tempfile to create a temporary file that will be automatically cleaned up
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=True) as temp_file:
                # Save report to temporary file
                report.to_csv(temp_file.name, index=False)
                
                # Upload to S3
                if upload_file_to_s3(temp_file.name, self.bucket_name, s3_key):
                    s3_url = get_s3_url(self.bucket_name, s3_key)
                    print(f"\nUploaded report for {instructor} ({email}) to S3")
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
                            'name': instructor,
                            's3_url': s3_url
                        })
        
        # Save not found contacts
        if not_found_contacts:
            save_not_found_contacts(not_found_contacts, 'output/instructor_reports') 