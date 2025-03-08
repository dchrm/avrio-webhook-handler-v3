import requests
import time
import logging
from requests.exceptions import HTTPError, RequestException
from ..utils.logging_config import setup_logging
import xml.etree.ElementTree as ET
import json
import re

# apply logging config file
setup_logging()

class APIRequestHandler:
    """Base class for handling API requests to the Karbon API."""
    
    def __init__(self, bearer_token, access_key, base_url='https://api.karbonhq.com/v3'):
        self.bearer_token = bearer_token
        self.access_key = access_key
        self.base_url = base_url

    def _send_request(self, method, endpoint, data=None, params=None, max_retries=10):
        """Sends an HTTP request to the specified endpoint."""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.bearer_token}',
            'AccessKey': self.access_key
        }
        
        retries = 0
        while retries < max_retries:
            try:
                response = requests.request(method, url, headers=headers, json=data, params=params)
                response.raise_for_status()  # Raises an HTTPError for bad responses
                logging.info(f"Request successful: {method} {url}")
                logging.info("Trying to return response.json()")
                try :
                    return response.json()
                except :
                    return response.text
            except HTTPError as e:
                if e.response.status_code == 429:
                    try_after = e.response.headers.get('Retry-After')
                    if try_after:
                        logging.warning(f"Rate limit exceeded: {method} {url} - 429 Too Many Requests. Retry after {try_after} seconds.")
                        time.sleep(int(try_after))
                    else:
                        logging.warning(f"Rate limit exceeded: {method} {url} - 429 Too Many Requests. No Retry-After header provided. Retrying in 1 second.")
                        time.sleep(1)
                    retries += 1
                else:
                    logging.error(f"HTTP error: {method} {url} - {e.response.status_code} {e.response.text}")
                    raise
            except RequestException as e:
                logging.error(f"Request exception: {method} {url} - {e}")
                raise
            except Exception as e:
                logging.error(f"Unhandled exception: {method} {url} - {e}")
                raise
        logging.error(f"Max retries exceeded for: {method} {url}")
        raise HTTPError(f"Max retries exceeded for: {method} {url}")

    def get(self, endpoint, params=None):
        """Sends a GET request."""
        return self._send_request('GET', endpoint, params=params)

    def post(self, endpoint, data):
        """Sends a POST request."""
        return self._send_request('POST', endpoint, data=data)

    def put(self, endpoint, data):
        """Sends a PUT request."""
        return self._send_request('PUT', endpoint, data=data)

    def delete(self, endpoint):
        """Sends a DELETE request."""
        return self._send_request('DELETE', endpoint)

    def patch(self, endpoint, data):
        """Sends a PATCH request."""
        return self._send_request('PATCH', endpoint, data=data)
    
class Entities(APIRequestHandler):
    def __init__(self, bearer_token, access_key):
        super().__init__(bearer_token, access_key)
    
    def get_entity_by_key(self, entitiy_key, entitiy_type, parameters=None):
        """Gets a single entity using the entity's key. Optionally add parameters"""
        endpoint = f"{entitiy_type}s"
        endpoint = f"{endpoint}/{entitiy_key}"
        return self.get(endpoint, parameters)

    def extract_json_from_description(self, description):
        """
        Extracts JSON content from the description field of a work item.
        The JSON content is enclosed within [JSON][/JSON] tags.
        
        Args:
            description (str): The description field containing JSON data.
        
        Returns:
            dict: The extracted JSON content as a dictionary.
        """
        try:
            # Use regular expression to find JSON content between [JSON] and [/JSON] tags
            match = re.search(r'\[JSON\](.*?)\[/JSON\]', description, re.DOTALL)
            if match:
                json_content = match.group(1)
                return json.loads(json_content)
            else:
                logging.warning("No JSON content found in the description.")
                return None
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON content: {e}")
            return None

class Notes(APIRequestHandler):
    def __init__(self, bearer_token, access_key):
        super().__init__(bearer_token, access_key)

    def add_note(self, subject, body, timelines, assignee=None, todo_date=None, due_date=None):
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
            "AuthorEmailAddress": "karbonbot@avriopro.com",
            "Subject": subject,
            "Body": body,
            "DueDate": due_date,
            "TodoDate": todo_date,
            "Timelines": timelines
        }
        return self.post(endpoint, data)

class GhenXMLReader: # for use with xml stored in work description
    def __init__(self, xml_data):
        self.root = ET.fromstring(xml_data)

    def get_cascaded_works(self):
        return [
            {
                "title": work.get("title"),
                "template_key": work.get("template_key"),
                "trigger_status": work.get("trigger_status")
            }
            for work in self.root.findall("Cascaded_Work")
        ]

# check to see if a webhook is from karbon.
def is_karbon_webhook(webhook_data):
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

