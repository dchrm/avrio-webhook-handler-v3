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

    def send_business_card(self, first_name, last_name, email_address, contact_name, contact_key, contact_type, work_item_name, work_item_key, work_type):
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
        logging.info('Received request to send to AskNicely')

        headers = {
            'Content-Type': 'application/json',
            'X-apikey': self.api_key
        }
        params = {
            'email': email_address,
            'firstname': first_name,
            'lastname': last_name,
            'addcontact': False,
            'triggeremail': True, # remove after testing
            'delayminutes': 0, # ask_nicely_minutes_delay,
            'contact_name_c': contact_name,
            'contact_key_c': contact_key,
            'contact_type_c': contact_type,
            'work_item_name_c': work_item_name,
            'work_item_key_c': work_item_key,
            'work_type_c': work_type
        }

        try:
            response = requests.post(self.base_url, params=params, headers=headers)
            if response.status_code == 201:
                logging.info('Request sent to Ask Nicely successfully.')
            else:
                logging.error(f"Failed to send data: {response.status_code}, {response.text}")
        except requests.RequestException as e:
            logging.error(f"An error occurred: {e}")
            raise RuntimeError(f"An error occurred while sending data to Ask Nicely: {e}")

        return response

# Usage example:
if __name__ == "__main__":

    # imports for test
    import os
    from dotenv import load_dotenv

    # Load the correct environmental variables
    env = os.environ.get('ENVIRONMENT', 'test')
    dotenv_path = f".env.{env}"
    load_dotenv(dotenv_path=dotenv_path)

    # get asknicely api key
    asknicely_api_key = os.getenv('ASKNICELY_API_KEY')
    api_key = os.getenv('ASKNICELY_API_KEY')
    print(api_key)
    ask_nicely = AskNicelyAPI(api_key)
    response = ask_nicely.send_business_card(
        first_name='John',
        last_name='Doe',
        email_address='m@dchr.me',
        contact_name='Company XYZ',
        contact_key='123abc',
        contact_type='Organization',
        work_item_name='Project Alpha',
        work_item_key='456def',
        work_type='Consulting'
    )
    print(response.status_code, response.json())
