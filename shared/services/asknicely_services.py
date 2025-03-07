import requests
import logging
from utils.logging_config import setup_logging
from utils.config import ask_nicely_minutes_delay

# apply logging config file
setup_logging()

class AskNicelyAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://avriosolutions.asknice.ly/api/v1/contact/trigger'

    def send_business_card(self, first_name, last_name, email_address, client_name, client_key, client_type, work_item_name, work_item_key, work_type):
        """
        Send business card information from Karbon to Ask Nicely via API to trigger an NPS survey.

        Parameters:
            first_name (str): First name of the person.
            last_name (str): Last name of the person.
            email_address (str): Email address of the person.
            contact_name (str): The name of the contact for whom the work was done.
            contact_key (str): Karbon's unique identifier for the contact.
            contact_type (str): Type of contact (Contact or Organization is expected).
            work_item_name (str): Name of the work item associated with the contact.
            work_item_key (str): Unique identifier for the work item.
            work_type (str): Type of work done.

        Returns:
            Response object from the requests module.
        """
        logging.info('Received request to send contact ifno to AskNicely for an NPS survey')

        headers = {
            'Content-Type': 'application/json',
            'X-apikey': self.api_key
        }
        params = {
            'email': email_address,
            'firstname': first_name,
            'lastname': last_name,
            'addcontact': False,
            # 'triggeremail': True, # remove after testing
            'delayminutes': 1440,
            'client_name_c': client_name,
            'client_key_c': client_key,
            'client_type_c': client_type,
            'work_item_name_c': work_item_name,
            'work_item_key_c': work_item_key,
            'work_type_c': work_type
        }

        try:
            logging.info("Trying to POST contact information to AskNicely.")
            response = requests.post(self.base_url, params=params, headers=headers)
            logging.info(f"Success! Response: {str(response.status_code)} | {str(response.text)}")
            if response.status_code == 201:
                logging.info('Request sent to Ask Nicely successfully.')
            else:
                logging.error(f"Failed to send data: {response.status_code}, {response.text}")
        except requests.RequestException as e:
            logging.error(f"An error occurred: {e}")
            raise RuntimeError(f"An error occurred while sending data to Ask Nicely: {e}")

        return response

# Used for testing:
if __name__ == "__main__":
    import os
