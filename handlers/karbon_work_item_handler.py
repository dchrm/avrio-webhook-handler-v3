import datetime
from datetime import timezone, timedelta
from shared.services.karbon_services import Entities, Notes
from shared.task_functions.send_contacts_to_asknicely import get_contact_information_and_send_surveys_to_asknicely as nps
from shared.task_functions.cascade_work import main as cascade_work
import logging
import os
import re
import xml.etree.ElementTree as ET
# from dotenv import load_dotenv
from shared.utils.logging_config import setup_logging

# apply logging config file
setup_logging()

# add your environment variables here and associated descriptions. descriptions used for logging only.
env_variables = [
    {
        'key': 'KARBON_TENANT_KEY',
        'description': "Karbon tenant key"
    },
    {
        'key': 'NPS_ELIGIBLE_WORK_TYPES',
        'description': "work types targeting for NPS surveys"
    },
    {
        'key': 'ASKNICELY_API_KEY',
        'description': "AskNicely api key for sending NPS surveys"
    }
]

# initialize the environment variables dictionary.
environment_variables = {}

def load_env_variable(key, description):
    logging.info(f"Trying to load {key} to get {description}.")
    value = os.getenv(key)
    if value is not None:
        logging.info(f"Success! Loaded {key}.")
        return value
    else:
        logging.warning(f"{key} not found in environment variables.")
        return None

# get environment variables
for var in env_variables:
    variable = var['key']
    description = var['description']
    environment_variables[variable] = load_env_variable(variable, description)

now = datetime.datetime.now(timezone.utc)

def handle_null_work(work_item_details, karbon_bearer_token, karbon_access_key) -> None:
    logging.info("Request to handle null work type received. - karbon_work_item_handler.handle_null_work")

    # set values from supplied data.
    work_item_title = work_item_details['Title']
    work_item_key = work_item_details['WorkItemKey']
    note_assignee = work_item_details['AssigneeEmailAddress']
    note_timelines = [{"EntityType": "WorkItem", "EntityKey": f"{work_item_key}"}]

    # Use timezone-aware datetime.
    note_todo_datetime = now
    note_due_datetime = now

    note_subject = "URGENT: This work item does not have a work type"
    note_body = f"""
    <p>{work_item_title} does not have a work type. Please update the work type.</p><br>
    <p>Link: <a href='https://app2.karbonhq.com/{environment_variables['KARBON_TENANT_KEY']}#/work/basic-details/{work_item_key}'>Work Item Details</a></p>
    """

    try:
        logging.info("Trying to send note to Karbon. - karbon_work_item_handler.handle_null_work")
        result = Notes(karbon_bearer_token,karbon_access_key).add_note(note_subject,note_body,note_timelines,note_assignee,note_todo_datetime,note_due_datetime)
        logging.info(f"Successfully sent note to work item. Response: {result}")
    except Exception as e:
        logging.error(f"Failed to add note with error: {e}")
    

def work_item_handler(data, karbon_bearer_token, karbon_access_key) -> None:
    logging.info("Request to handle work item received.")

    # send work to cascade_work function
    try:
        logging.info("Trying to send work to cascade_work function.")
        cascade_work(data)
        logging.info("Successfully sent work to cascade_work function.")
    except Exception as e:
        logging.error(f"Failed to send work to cascade_work function with error: {e}")

    # set values for next api call
    entity_key = data['ResourcePermaKey']
    entity_type = data['ResourceType']

    # get full work item details
    logging.info('Requesting full Work Item from Karbon.')
    work_item_details = Entities(karbon_bearer_token,karbon_access_key).get_entity_by_key(entity_key,entity_type)

    # Check if the work item is eligible for net promoter score (nps) and send it along if so.
    work_item_status = work_item_details['PrimaryStatus']
    work_item_type = work_item_details['WorkType']
    eligible_work_types = environment_variables['NPS_ELIGIBLE_WORK_TYPES']

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
        if time_difference <= timedelta(seconds=90):
            # get asknicely api key
            try:
                logging.info('Try to get AskNicely api key from environmental variables.')
                asknicely_api_key = environment_variables['ASKNICELY_API_KEY']
            except:
                logging.error('Could not load AskNicely API key.')

            # send information to asknicely.
            logging.info('Attempting to send NPS survye trigger to AskNicely.')
            nps(karbon_bearer_token,karbon_access_key,work_item_details,asknicely_api_key)
        
        else:
            logging.info(f"Not eligible for NPS because work item was completed {time_difference} hours ago. Must be within 1 hour.")
    else:
        logging.info(f"Work Item not eligible for NPS. Work Item status: {work_item_status}")
