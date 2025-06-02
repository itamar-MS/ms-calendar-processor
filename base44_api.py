import requests
from typing import Dict, List, Optional
from datetime import datetime
import json
import os
from dotenv import load_dotenv

class Base44API:
    def __init__(self, api_key: str = None):
        if api_key is None:
            load_dotenv()  # Load environment variables from .env file
            api_key = os.getenv('BASE44_API_KEY')
            if not api_key:
                raise ValueError("BASE44_API_KEY environment variable is not set")
        
        self.api_key = api_key
        self.base_url = "https://app.base44.com/api/apps/6836209fe04732f5f6cc26f4"
        self.headers = {
            'api_key': api_key,
            'Content-Type': 'application/json'
        }

    def fetch_time_entries(
        self,
        faculty_email: Optional[str] = None,
        date: Optional[str] = None,
        month: Optional[str] = None,
        activity_type: Optional[str] = None,
        hours: Optional[float] = None,
        description: Optional[str] = None,
        course_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch time entries from Base44 API with optional filters.
        
        Args:
            faculty_email: Filter by faculty email
            date: Filter by specific date (YYYY-MM-DD)
            month: Filter by month (YYYY-MM)
            activity_type: Filter by activity type
            hours: Filter by hours
            description: Filter by description
            course_name: Filter by course name
            
        Returns:
            List of time entry dictionaries
        """
        url = f"{self.base_url}/entities/TimeEntry"
        
        # Build query parameters
        params = {}
        if faculty_email:
            params['faculty_email'] = faculty_email
        if date:
            params['date'] = date
        if month:
            params['month'] = month
        if activity_type:
            params['activity_type'] = activity_type
        if hours:
            params['hours'] = hours
        if description:
            params['description'] = description
        if course_name:
            params['course_name'] = course_name

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching time entries: {e}")
            return []

    def bulk_add_time_entries(self, records: List[Dict]) -> bool:
        """
        Bulk add time entries to Base44.
        
        Args:
            records: List of time entry dictionaries to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        url = f"{self.base_url}/entities/TimeEntry/bulk"
        
        try:
            response = requests.post(url, headers=self.headers, json=records)
            response.raise_for_status()
            print(f"Successfully added {len(records)} time entries")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error bulk adding time entries: {e}")
            return False

    def delete_time_entry(self, record_id: str) -> bool:
        """
        Delete a time entry from Base44.
        
        Args:
            record_id: ID of the record to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        url = f"{self.base_url}/entities/TimeEntry/{record_id}"
        
        try:
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()
            print(f"Successfully deleted time entry {record_id}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error deleting time entry: {e}")
            return False

    def bulk_delete_time_entries(self, record_ids: List[str]) -> bool:
        """
        Bulk delete time entries from Base44.
        
        Args:
            record_ids: List of record IDs to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        success = True
        for record_id in record_ids:
            if not self.delete_time_entry(record_id):
                success = False
        return success

def main():
    # Example usage
    api = Base44API()  # Will automatically use API key from environment
    
    # Example: Fetch all time entries
    time_entries = api.fetch_time_entries()
    print(json.dumps(time_entries, indent=2))
    
    # Example: Fetch time entries with filters
    filtered_entries = api.fetch_time_entries(
        faculty_email="itamar@masterschool.com",
        month="2025-05"
    )
    print(json.dumps(filtered_entries, indent=2))

if __name__ == "__main__":
    main() 