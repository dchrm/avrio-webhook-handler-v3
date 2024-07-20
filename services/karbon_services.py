import requests
import logging
from requests.exceptions import HTTPError, RequestException
from utils.logging_config import setup_logging
from datetime import date
from utils.config import BASE_URL, DEFAULT_AUTHOR_EMAIL

# apply logging config file
setup_logging()

class APIRequestHandler:
    """Base class for handling API requests to the Karbon API."""
    
    def __init__(self, bearer_token: str, access_key: str, base_url: str = BASE_URL):
        self.bearer_token = bearer_token
        self.access_key = access_key
        self.base_url = base_url

    def _send_request(
            self, 
            method: str, 
            endpoint: str, 
            data: dict | None = None, 
            params: dict | None = None
        ) -> dict:
        """Sends an HTTP request to the specified endpoint."""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.bearer_token}',
            'AccessKey': self.access_key
        }
        
        try:
            response = requests.request(method, url, headers=headers, json=data, params=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            logging.info(f"Request successful: {method} {url}")
            return response.json()  # Returns JSON response
        except HTTPError as e:
            logging.error(f"HTTP error: {method} {url} - {e.response.status_code} {e.response.text}")
            raise
        except RequestException as e:
            logging.error(f"Request exception: {method} {url} - {e}")
            raise
        except Exception as e:
            logging.error(f"Unhandled exception: {method} {url} - {e}")
            raise

    def get(self, endpoint: str, params: dict | None = None):
        """Sends a GET request."""
        return self._send_request('GET', endpoint, params=params)

    def post(self, endpoint: str, data: dict):
        """Sends a POST request."""
        return self._send_request('POST', endpoint, data=data)

    def put(self, endpoint: str, data: dict):
        """Sends a PUT request."""
        return self._send_request('PUT', endpoint, data=data)

    def delete(self, endpoint: str):
        """Sends a DELETE request."""
        return self._send_request('DELETE', endpoint)

    def patch(self, endpoint: str, data: dict):
        """Sends a PATCH request."""
        return self._send_request('PATCH', endpoint, data=data)
    
class Entities(APIRequestHandler):
    def __init__(self, bearer_token: str, access_key: str):
        super().__init__(bearer_token, access_key)
    
    def get_entity_by_key(self, entitiy_key: str, entitiy_type: str, parameters: dict | None = None) -> dict:
        """Gets a single entitiy using the entities's key. Optionally add parameters"""
        endpoint = f"{entitiy_type}s"
        endpoint = f"{endpoint}/{entitiy_key}"
        return self.get(endpoint,parameters)

class Notes(APIRequestHandler):
    def __init__(self, bearer_token: str, access_key: str):
        super().__init__(bearer_token, access_key)

    def add_note(
            self, 
            subject: str, 
            body: str, 
            timelines: dict, 
            assignee: str | None = None, 
            todo_date: date | None = None, 
            due_date: date | None = None
        ) -> dict:
        """
        Adds a note with provided information to Karbon.
        EXAMPLE TIMELINES:
        'Timelines': [
            {
                "EntityType": 'WorkItem',
                "EntityKey": 'work_key'
            },
            {
                "EntityType": 'Organization',
                "EntityKey": 'organizaiton_key'
            }
        ]
        """
        endpoint = 'Notes'
        
        # build the note body
        gehn_signature = "</br></br>Thank you,</br>Gehn</br><i>Automation Bot</i>" # Gehn's signature block
        body = f"Hi there,</br></br>{body}{gehn_signature}"

        # build data
        data = {
            "AssigneeEmailAddress": assignee,
            "AuthorEmailAddress": DEFAULT_AUTHOR_EMAIL,
            "Subject": subject,
            "Body": body,
            "DueDate": due_date,
            "TodoDate": todo_date,
            "Timelines": timelines
        }
        return self.post(endpoint, data)

# check to see if a webhook is from karbon.
def is_karbon_webhook(webhook_data: dict) -> bool:
    # Check if the necessary headers or body keys are present
    try:
        # Check for specific body keys typical for Karbon
        logging.info("Main Handler - is_karbon_webhook:Checking to see if received data looks like a Karbon webhook.")
        body_keys = ['ResourcePermaKey', 'ResourceType', 'ActionType']
        if all(key in webhook_data for key in body_keys):
            logging.info("Main Handler - is_karbon_webhook:Data appears to be a karbon webhook.")
            # Additional checks can be made here, e.g., specific values or formats
            return True
        return False
    except KeyError:
        # If any key is missing, it's not a valid Karbon webhook
        return False
