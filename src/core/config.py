"""
Configuration management for the calendar extractor.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the calendar extractor."""
    
    # Database configuration
    CAMPUS_DB_CONN = os.getenv('CAMPUS_DB_CONN')
    LMS_DB_CONN = os.getenv('LMS_DB_CONN')
    
    # AWS configuration
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
    
    # API Keys
    HUBSPOT_API_KEY = os.getenv('HUBSPOT_API_KEY')
    BASE44_API_KEY = os.getenv('BASE44_API_KEY')
    
    # File paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATA_DIR = PROJECT_ROOT / 'data'
    OUTPUT_DIR = PROJECT_ROOT / 'output'
    
    # HubSpot configuration
    HUBSPOT_PROPERTY = 'monthly_report___june'
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        required_vars = [
            'CAMPUS_DB_CONN',
            'HUBSPOT_API_KEY',
            'BASE44_API_KEY'
        ]
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True
    
    @classmethod
    def get_database_connection_string(cls, db_name: str) -> str:
        """Get database connection string by name."""
        if db_name == 'CampusDB':
            return cls.CAMPUS_DB_CONN
        elif db_name == 'LMSDB':
            return cls.LMS_DB_CONN
        else:
            raise ValueError(f"Unknown database name: {db_name}") 