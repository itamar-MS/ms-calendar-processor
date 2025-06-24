import boto3
from botocore.exceptions import ClientError
import os
from pathlib import Path
import json
import uuid

def create_s3_bucket(bucket_name, region='us-east-1'):
    """Create an S3 bucket if it doesn't exist."""
    try:
        s3_client = boto3.client('s3', region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} created successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"Bucket {bucket_name} already exists")
        else:
            raise e

def upload_file_to_s3(file_path, bucket_name, s3_key=None):
    """Upload a file to S3 bucket."""
    if s3_key is None:
        s3_key = os.path.basename(file_path)
    
    try:
        s3_client = boto3.client('s3')
        s3_client.upload_file(
            file_path, 
            bucket_name, 
            s3_key,
            ExtraArgs={
                'ContentType': 'text/csv'
            }
        )
        print(f"Successfully uploaded {file_path} to s3://{bucket_name}/{s3_key}")
        return True
    except ClientError as e:
        print(f"Error uploading {file_path}: {e}")
        return False

def get_s3_url(bucket_name, s3_key):
    """Generate the public S3 URL for a file."""
    return f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

def generate_unique_filename(instructor_name, date, original_filename):
    """Generate a unique filename using a secure UUID, instructor name, and date."""
    # Get the file extension
    _, ext = os.path.splitext(original_filename)
    # Generate a full UUID
    full_uuid = str(uuid.uuid4())
    # Create a safe instructor name
    safe_name = instructor_name.replace(' ', '_')
    # Format: name_date_uuid.csv
    return f"{safe_name}_{date}_{full_uuid}{ext}" 