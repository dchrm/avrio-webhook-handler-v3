import datetime
from datetime import timezone, timedelta
from services.karbon_services import Entities
from task_functions.send_contacts_to_asknicely import get_contact_information_and_send_surveys_to_asknicely as nps
import logging
import os
# from dotenv import load_dotenv
from utils.logging_config import setup_logging

# apply logging config file
setup_logging()

def work_item_handler(data, karbon_bearer_token, karbon_access_key):

    # logging.info('Attempt to load environment.')
    # # Load the correct environmental variables
    # load_dotenv('..env')
    # logging.info(f"Loaded envirtonment at path: {dotenv_path}")

    # set values for next api call
    entity_key = data['ResourcePermaKey']
    entity_type = data['ResourceType']

    # get full work item details
    logging.info('Requesting full Work Item from Karbon.')
    work_item_details = Entities(karbon_bearer_token,karbon_access_key).get_entity_by_key(entity_key,entity_type)

    # Check if the work item is eligible for net promoter score (nps) and send it along if so.
    work_item_status = work_item_details['PrimaryStatus']
    work_item_type = work_item_details['WorkType']
    eligible_work_types = [
        # 'Tax: Processing',
        'Internal'
    ]
    logging.info('Checking if work item is eligible for Net Promoter Score (NPS)')
    if work_item_status == 'Completed' and work_item_type in eligible_work_types:
        # Parse the CompletedDate to datetime object and set it to UTC timezone and compare to 
        completed_datetime = work_item_details['CompletedDate'] # get completed datetime from work item.
        completed_datetime = datetime.datetime.strptime(completed_datetime, '%Y-%m-%dT%H:%M:%SZ') # format time for comparison.
        completed_datetime = completed_datetime.replace(tzinfo=timezone.utc) # set completed time to UTC.
        current_datetime = datetime.datetime.now(timezone.utc) # Get the current datetime in UTC.
        time_difference = current_datetime - completed_datetime # Calculate the time difference between completed datetime and now.

        # Check if the work item was completed within the last hour
            # This avoids situations where work items are updated after they are completed.
            # Such situations will fail this test and won't be sent for NPS.
        logging.info('Check to see if work item was completed recently.')
        if time_difference <= timedelta(hours=1):
            # get asknicely api key
            try:
                logging.info('Try to get AskNicely api key from environmental variables.')
                asknicely_api_key = os.getenv('ASKNICELY_API_KEY')
            except:
                logging.error('Could not load AskNicely API key.')

            # send information to asknicely.
            logging.info('Attempting to send NPS survye trigger to AskNicely.')
            nps(karbon_bearer_token,karbon_access_key,work_item_details,asknicely_api_key)
        
        else:
            logging.info(f"Not eligible for NPS because work item was completed {time_difference} hours ago. Must be within 1 hour.")
    else:
        logging.info(f"Work Item not eligible for NPS. Work Item status: {work_item_status}")

# use for testing
if __name__ == "__main__":
    # imports for test
    import os