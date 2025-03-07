from services.karbon_services import Notes, Entities
from services.asknicely_services import AskNicelyAPI
import datetime
import logging
from utils.logging_config import setup_logging

# apply logging config file
setup_logging()

# get client details from work key 
def get_contact_information_and_send_surveys_to_asknicely(karbon_bearer_token, karbon_access_key, work_item_details, asknicely_api_key):

    logging.info('Received request to send contact information to AskNicely.')

    # initialize apis
    entities_api = Entities(karbon_bearer_token,karbon_access_key)
    notes_api = Notes(karbon_bearer_token,karbon_access_key)

    client_key = work_item_details['ClientKey']
    client_type = work_item_details['ClientType']
    client_name = work_item_details['ClientName']

    # handle organziation-type clients.
    logging.info(f"Checking client type and handling appropriately.")
    logging.info(f"Client: {client_name} | Client Type: {client_type} | Key: {client_key}")
    if client_type == 'Organization':
        logging.info("Client is an org.")
        # get contacts associated with the work item's organizaiton
        params = {'$expand': 'Contacts'}
        logging.info(f"Requesting full org details from Karbon.")
        organization_details = entities_api.get_entity_by_key(client_key,client_type,params)

        # pull out contacts information.
        logging.info("Found contacts attached to Org.")
        contacts = organization_details['Contacts']

        # Check to see if there are contacts associated. If not, add a note to Karbon.
        logging.info("Checking for contacts information attached to the Org.")
        if not contacts:
            logging.info("Cannot find any contact information.")
            note_subject = 'OH NO! No people connected to this organization'
            note_body = f"I tried to send out some NPS surveys because we just finished up the {work_item_details['Title']} for {work_item_details['ClientName']}, but I couldn't find any people attached to this organization. Please take care of this right away so I can send out NPS surveys in the future."
            timelines = [
                {'EntityType': 'WorkItem','EntityKey': work_item_details['WorkItemKey']},
                {'EntityType': work_item_details['ClientType'],'EntityKey': work_item_details['ClientKey']}
            ]
            
            assignee = work_item_details['AssigneeEmailAddress']

            logging.info("Adding note to the client and work item timelines.")
            notes_api.add_note(note_subject,note_body,timelines,assignee)

    elif client_type == 'Contact':
        logging.info("Client is a contact.")
        contacts = [{'ContactKey': client_key, 'FullName': client_name}]

    else:
        logging.info("Client is neither an org or a contact. Ending process.")
        return None
    
    

    # cycle throhgh each contact to get their business cards
    logging.info("Cycling through to find names and email addresses for AskNicely.")
    for contact in contacts:
        params = {'$expand': 'BusinessCards'}
        # get contact details for this contact.
        contact_key = contact['ContactKey']
        contact_name = contact['FullName']
        logging.info(f"Request contact details for contact. Name: {contact_name} | Key: {contact_key}")
        contact_details = entities_api.get_entity_by_key(contact_key,'Contact',params)

        # build list for asknicely
        ## first name
        logging.info("Checking for preferred name.")
        if contact_details['PreferredName'] not in ("", None):
            logging.info("Preferred name exists. Setting it as first name.")
            first_name = contact_details['PreferredName']
        else:
            logging.info("No preferred name set. Setting 'FirstName' to 'fist_name'.")
            first_name = contact_details['FirstName']
        ## last name
        last_name = contact_details['LastName']

        # search business cards for an appropriate email address.
        business_cards = contact_details['BusinessCards']
        logging.info("Looking up business cards for contact.")
        email = get_email_from_business_cards(business_cards,client_key)
        
        # set timelines for future use.
        timelines = [
            {'EntityType': 'WorkItem','EntityKey': work_item_details['WorkItemKey']},
            {'EntityType': work_item_details['ClientType'],'EntityKey': work_item_details['ClientKey']},
            {'EntityType': 'Contact','EntityKey': contact['ContactKey']}
        ]

        # if no email exists, add a note to the appropriate timelines.
        logging.info("Check if email exists.")
        if not email:
            logging.info("No email exists.")
            note_body = f"I tried to send an NPS survey to {contact['FullName']} after we finished their {work_item_details['Title']}, but I cannot locate an email address. Pleaes take care of this right away so I can send out their NPS survey."

            logging.info("Adding note to appropriate timelines asking for updated contact information.")
            assignee = work_item_details['AssigneeEmailAddress']
            add_note_for_missing_contact_information(karbon_bearer_token,karbon_access_key,assignee,timelines,note_body)
            # stopping the loop as no emails where found for this contact.
            break

        try: # send survey survye trigger to asknicely
            logging.info("Trying to send contact info to AskNicely for NPS survey.")
            result = AskNicelyAPI(asknicely_api_key).send_business_card(
                first_name,last_name,email,
                work_item_details['ClientName'],
                work_item_details['ClientKey'],
                work_item_details['ClientType'],
                work_item_details['Title'],
                work_item_details['WorkItemKey'],
                work_item_details['WorkType']
            )
            logging.info(f"Success. Response: {str(result)}")
            data = result.json()
            survey_sent = data["result"][0]["survey_sent"]
        except Exception as e:
            logging.error(f"Failed! Error: {str(e)}")

        if survey_sent == True: # check if the survey was sent.
            try: # add note to appropriate timelines about the NPS survey.
                logging.info("Trying to request Karbon to add not to timelines.")
                note_subject = "FYI: Sent NPS survey"
                note_body = f"I sent an NPS survey to {contact_name} after we completed '{work_item_details['Title']}' for '{client_name}'."
                result = Notes(karbon_bearer_token,karbon_access_key).add_note(note_subject,note_body,timelines)
                logging.info(f"Success! Response: {str(result)}")
            except Exception as e:
                logging.info(f"Failed! Error: {str(e)}")
        else:
            logging.info("Survey skipped due to rules.")

def get_email_from_business_cards(business_cards, client_key):
    primary_email = None

    # Cycle through each business card once to find the right email
    logging.info("Cycle through business cards to find email addresses.")
    for business_card in business_cards:
        # Extract emails from the current business card
        emails = business_card.get('EmailAddresses')
        logging.info("Found a business card. Checking if emails exist.")
        if not emails:
            logging.info("No emails on this business card.")
            continue  # Skip if no emails
        
        # Check if the business card matches the organization key
        logging.info("Checking if this business card is related to the org where the work happened.")
        if business_card.get('OrganizationKey') == client_key:
            logging.info("This business card is related to the org where the work happened.")
            email = emails[0]
            logging.info(f"Found at least one email on this business card. Returning the first email: {email}")
            return email  # Return the first email if it matches the client key
        
        # Check if the card is primary; save the email to return later if no better match is found
        logging.info("Checking if this business card is the primary card.")
        if business_card.get('IsPrimaryCard'):
            logging.info("This is the primary business card.")
            primary_email = emails[0]
            logging.info(f"Found at least one primary email address: {primary_email}")
    
    # Return the primary email if no organization-specific email was found
    if primary_email:
        logging.info(f"Returning primary email address: {primary_email}")
        return primary_email

    # As a last resort, return the first email found on any card
    logging.info("Couldn't find email address on primary or organization business card.")
    logging.info("Checking to see if any emails exist on any other cards.")
    for business_card in business_cards:
        logging.info("Found a card. Checking for an email address.")
        emails = business_card.get('EmailAddresses')
        if emails:
            logging.info("Found at least one email address.")
            email = emails[0]
            logging.info(f"Returning the first email found: {email}")
            return email
        logging.info("Found no email addresses.")
        return None  # Return None if no emails are found at all

def add_note_for_missing_contact_information(karbon_bearer_token,karbon_access_key,assignee_email,timelines,note_body) -> None:
    logging.info("Received request to add note to Karbon.")
    
    # Create a timezone-aware datetime object (using UTC as an example)
    utc_timezone = datetime.timezone.utc
    now = datetime.datetime.now(utc_timezone)
    iso_formatted_date = now.isoformat() # formatting for iso to include the time zone.

    note_subject = "OH NO! Missing contact information"

    try: # try to send note to karbon.
        logging.info("Trying to post note to Karbon.")
        result = Notes(karbon_bearer_token,karbon_access_key).add_note(note_subject,note_body,timelines,assignee_email,iso_formatted_date,iso_formatted_date)
        logging.info(f"Success! Response: {str(result)}")
    except Exception as e: # log any exceptions.
        logging.error(f"Failed! Error: {str(e)}")

# use for testing
if __name__ == "__main__":
    # imports for test
    import os