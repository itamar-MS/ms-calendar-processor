import os
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput
from hubspot.crm.contacts.exceptions import ApiException
from hubspot.crm.contacts.models import PublicObjectSearchRequest
import pandas as pd
from datetime import datetime

def get_hubspot_client():
    """Initialize and return a HubSpot client."""
    api_key = os.getenv('HUBSPOT_API_KEY')
    if not api_key:
        raise ValueError("HUBSPOT_API_KEY environment variable is not set")
    
    # Initialize client with the correct configuration
    client = HubSpot()
    client.access_token = api_key
    return client

def search_contact_by_email(client, email):
    """Search for a contact by email and return their ID if found."""
    try:
        # Create search request
        search_request = PublicObjectSearchRequest(
            filter_groups=[{
                "filters": [{
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": email
                }]
            }],
            limit=1
        )
        
        # Search for contacts with the given email
        response = client.crm.contacts.search_api.do_search(
            public_object_search_request=search_request
        )
        
        # If we found any contacts, return the first one's ID
        if response.total > 0:
            return response.results[0].id
        return None
    except ApiException as e:
        print(f"Error searching for contact with email {email}: {e}")
        return None

def update_contact_property(client, contact_id, property_name, value):
    """Update a contact's property."""
    try:
        properties = {
            property_name: value
        }
        simple_public_object_input = SimplePublicObjectInput(properties=properties)
        client.crm.contacts.basic_api.update(
            contact_id=contact_id,
            simple_public_object_input=simple_public_object_input
        )
        return True
    except ApiException as e:
        print(f"Error updating contact {contact_id}: {e}")
        return False

def save_not_found_contacts(not_found_contacts, output_dir):
    """Save a list of not found contacts to a CSV file."""
    if not not_found_contacts:
        return
    
    # Create DataFrame
    df = pd.DataFrame(not_found_contacts, columns=['email', 'name', 's3_url'])
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"not_found_contacts_{timestamp}.csv"
    output_path = os.path.join(output_dir, filename)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"\nSaved {len(not_found_contacts)} not found contacts to {output_path}") 