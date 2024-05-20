import azure.functions as func
import logging
import os
from handlers.karbon_work_item_handler import work_item_handler
from handlers.karbon_notes_handler import notes_handler
from handlers.karbon_contacts_handler import contacts_handler
from services.karbon_services import is_karbon_webhook
import asyncio

# Get API keys and other environment variables
karbon_access_key = os.getenv('KARBON_ACCESS_KEY')
karbon_bearer_token = os.getenv('KARBON_BEARER_TOKEN')
azure_logic_app_handler_url = os.getenv('AZURE_LOGIC_APP_HANDLER')

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

async def webhook_processor(req) -> None:

    # Log the request headers and body
    logging.info(f"Request Headers: {req.headers}")
    logging.info(f"Request Body: {req.get_body()}")

    # Parse the request body safely
    try:
        logging.info("Trying to get JSON body of request.")
        req_body = req.get_json()
        logging.info(f"Parsed Request Body: {req_body}")
    except ValueError:
        logging.error("Main Handler - Invalid JSON received.")
    
    # Process the webhook if it's valid for Karbon
    logging.info("Main Handler - Checking to see if webhook is from Karbon.")
    if is_karbon_webhook(req_body):
        logging.info("Main Handler - Webhook appears to be from Karbon.")
    else:
        logging.info("Main Handler - Request did not qualify as a Karbon webhook.")

    resource_type = req_body.get('ResourceType')
    logging.info(f"Main Handler - Handling {resource_type} event.")

    # Mapping of Karbon resource types to handler functions
    karbon_event_handlers = {
        'WorkItem': work_item_handler,
        'Contact': contacts_handler,
        'Note': notes_handler
    }

    if resource_type not in karbon_event_handlers:
        logging.warning(f"Main Handler - Received unhandled event type: {resource_type}")
        return

    # Execute the handler function associated with the resource type
    try:
        logging.info("Main Handler - Trying to send webhook to associated sub-handler.")
        handler_function = karbon_event_handlers[resource_type]
        handler_function(req_body, karbon_bearer_token, karbon_access_key)
        logging.info(f"Main Handler - {resource_type} event processed successfully.")
    except Exception as e:
        logging.error(f"Main Handler - Error processing the {resource_type} event: {str(e)}", exc_info=True)    

@app.route(route="MainWebhookHandler")
async def MainWebhookHandler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function received a request.")

    try:
        # Log request details
        logging.info('Trying to send to webhook_processor.')
        logging.info(f"Request Headers: {req.headers}")
        logging.info(f"Request Body: {req.get_body()}")

        # Start webhook processing asynchronously
        await webhook_processor(req)

        # Return the response immediately and log the response details
        response = func.HttpResponse("Webhook accepted", status_code=202, headers={"Content-Type": "application/json"})
        logging.info(f"Response Status Code: {response.status_code}")
        logging.info(f"Response Headers: {response.headers}")
        logging.info(f"Response Body: {response.get_body()}")
        return response

    except Exception as e:
        logging.error(f"Exception in MainWebhookHandler: {str(e)}")
        return func.HttpResponse("Server error", status_code=500, headers={"Content-Type": "application/json"})