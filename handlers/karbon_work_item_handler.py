import datetime
from datetime import timezone, timedelta
from services.karbon_services import Entities, Notes, GhenXMLReader
from task_functions.send_contacts_to_asknicely import get_contact_information_and_send_surveys_to_asknicely as nps
import logging
import os
import re
import xml.etree.ElementTree as ET
# from dotenv import load_dotenv
from utils.logging_config import setup_logging

# apply logging config file
setup_logging()
try: # try getting Karbon Tenant Key from environment variables.
    logging.info("Try to load the Karbon Tenant from environment variables. - karbon_work_item_handler")
    karbon_tenant_key = os.getenv('KARBON_TENANT_KEY')
    logging.info("Successfully aquired Karbon Tenant Key from environtment variables. - karbon_work_item_handler")
except Exception as e: # log any errors.
    logging.error(f"Failed to get Karbon Tenant Key with error: {e}")

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
    <p>Link: <a href='https://app2.karbonhq.com/{karbon_tenant_key}#/work/basic-details/{work_item_key}'>Work Item Details</a></p>
    """

    try:
        logging.info("Trying to send note to Karbon. - karbon_work_item_handler.handle_null_work")
        result = Notes(karbon_bearer_token,karbon_access_key).add_note(note_subject,note_body,note_timelines,note_assignee,note_todo_datetime,note_due_datetime)
        logging.info(f"Successfully sent note to work item. Response: {result}")
    except Exception as e:
        logging.error(f"Failed to add note with error: {e}")

# def handle_inserted_work(work_item_details, karbon_bearer_token, karbon_access_key) -> None:
#     # check if xml exists in the description
#     xml_pattern = r"<gehn>.*?</gehn>"
#     match = re.search(xml_pattern, text, re.DOTALL)
#     if match:
#         xml_data = match.group()
        
#         cascaded_works = GhenXMLReader(xml_data).get_cascaded_works()
#         for work in cascaded_works:
#             title = work['title']
#             template_key = work['template_key']
#             trigger_status = work['trigger_status']

#             Entities(karbon_bearer_token,karbon_access_key)

#         # take some actions here...


#     else:
#         # add xml as text here...
#         xml_template = "*** DO NOT TYPE BELOW THIS LINE ***\n***********************************************\n<Ghen>\n    <Flags>\n        <Flag name='cascade' value='false'/>\n        <!-- Additional flags can be added here -->\n    </Flags>\n    <Cascade_Settings>\n        <Next_Work key='example_key' title='example title'>\n        <!-- Additional work can be added here -->\n    </Cascade_Settings>\n</Ghen>"

def handle_cascading_work(work_item_details, karbon_bearer_token, karbon_access_key) -> None:
    logging.info("Request to handle cascading work item received.")

    dict_of_next_work = {
        'incoming work type': {'NextWorkTitle': 'example next work item title', 'NextWorkTemplateKey': 'next work template key'},
        'incoming work type2': {'NextWorkTitle': 'example next work item title', 'NextWorkTemplateKey': 'next work template key'}
    }

    incoming_work_type = work_item_details['WorkType']
    next_work_title = dict_of_next_work[incoming_work_type]['next work title']
    next_work_template_key = dict_of_next_work[incoming_work_type]['NextWorkTemplateKey']

    data = {
        "Title": next_work_title,
        "ClientKey": work_item_details['ClientKey'],
        "ClientType": work_item_details['ClientType'],
        "StartDate": now,
        "RelatedClientGroupKey": work_item_details['RelatedClientGroupKey'],
        "WorkTemplateKey": next_work_template_key
    }

    try: # Try sending new work item to Karbon.
        logging.info("Trying to send next work item to Karbon")
        result = Entities(karbon_bearer_token,karbon_access_key).post('WorkItems',data)
        logging.info(f"Successfully added work item. Response: {result}")
    except Exception as e:
        logging.error(f"Failed to add work item. Error: {e}")

    note_subject = "FYI: Processed cascading work item."
    note_body =f"""
    <p><a href="https://app2.karbonhq.com/{karbon_tenant_key}#/work/{work_item_details['WorkItemKey']}">{work_item_details['Title']}</a> completed so I added 
    <a href="https://app2.karbonhq.com/{karbon_tenant_key}#/work/{result['WOrkItemKey']}">{next_work_title}</a>.</p>
    """
    note_timelines = [
        {
        "EntityType": "WorkItem",
        "EntityKey": work_item_details['WorkItemKey']
        },
        {
        "EntityType": "WorkItem",
        "EntityKey": result['WorkItemKey']
        }
    ]

    try: # Try adding a note to each work timeline.
        logging.info("Trying to add note to incoming and next work item timelines.")
        result = Notes(karbon_bearer_token,karbon_access_key).add_note(note_subject,note_body,note_timelines)
        logging.info(f"Successfully added note to karbon. Result: {str(result)}")
    except Exception as e:
        logging.error(f"Failed to add note. Error: {str(e)}")
    
def work_item_handler(data, karbon_bearer_token, karbon_access_key) -> None:
    logging.info("Request to handle work item received.")

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
        if time_difference <= timedelta(seconds=90):
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