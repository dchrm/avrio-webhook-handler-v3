import azure.functions as func
import logging
import os
from handlers.karbon_work_item_handler import work_item_handler
from handlers.karbon_notes_handler import notes_handler
from handlers.karbon_contacts_handler import contacts_handler
from services.karbon_services import is_karbon_webhook
import asyncio

async def webhook_processor(req) -> None:

    logging.info("Received a request to handle a webhook. - webhook_processor")

    try:
        logging.info("Trying to load access keys and other environment variables. - webhook_processor")
        # Get API keys and other environment variables
        karbon_access_key = os.getenv('KARBON_ACCESS_KEY')
        karbon_bearer_token = os.getenv('KARBON_BEARER_TOKEN')
        azure_logic_app_handler_url = os.getenv('AZURE_LOGIC_APP_HANDLER')
    except Exception as e:
        logging.error(f"Failed to load environment variables with error: {str(e)}")
        return


    # Log the request headers and body
    logging.info(f"Request Headers: {req.headers}")
    logging.info(f"Request Body: {req.get_body()}")

    # Parse the request body safely
    try:
        logging.info("Trying to get JSON body of request. - webhook_processor")
        req_body = req.get_json()
        logging.info(f"Parsed Request Body: {req_body}")
    except ValueError:
        logging.error("Invalid JSON received. - webhook_processor")
    
    # Process the webhook if it's valid for Karbon
    logging.info("Checking to see if webhook is from Karbon. - webhook_processor")
    if is_karbon_webhook(req_body):
        logging.info("Webhook appears to be from Karbon. - webhook_processor")
    else:
        logging.info("Request did not qualify as a Karbon webhook. - webhook_processor")

    resource_type = req_body.get('ResourceType')
    logging.info(f"Handling {resource_type} event. - webhook_processor")

    # Mapping of Karbon resource types to handler functions
    karbon_event_handlers = {
        'WorkItem': work_item_handler,
        'Contact': contacts_handler,
        'Note': notes_handler
    }

    if resource_type not in karbon_event_handlers:
        logging.warning(f"Received unhandled event type: {resource_type} - webhook_processor")
        return

    # Execute the handler function associated with the resource type
    try:
        logging.info("Trying to send webhook to associated sub-handler. - webhook_processor")
        handler_function = karbon_event_handlers[resource_type]
        handler_function(req_body, karbon_bearer_token, karbon_access_key)
        logging.info(f"{resource_type} event processed successfully. - webhook_processor")
    except Exception as e:
        logging.error(f"Error processing the {resource_type} event: {str(e)}", exc_info=True)


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
@app.route(route="MainWebhookHandler", methods=['POST'])
async def MainWebhookHandler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Received a request. - MainWebhookHandler")

    try:
        # Log request details
        logging.info('Trying to send webhook to webhook_processor. - MainWebhookHandler')
        logging.info(f"Request Headers: {req.headers}")
        logging.info(f"Request Body: {req.get_body()}")

        # Start webhook processing asynchronously
        # asyncio.create_task(webhook_processor(req))
        await webhook_processor(req)

        # Return the response immediately and log the response details
        logging.info("Returning response to webhook sender. - MainWebhookHandler")
        response = func.HttpResponse("Webhook accepted", status_code=202, headers={"Content-Type": "application/json"})
        logging.info(f"Response Status Code: {response.status_code}")
        logging.info(f"Response Headers: {response.headers}")
        logging.info(f"Response Body: {response.get_body()}")
        return response

    except Exception as e:
        logging.error(f"Exception in MainWebhookHandler: {str(e)}")
        logging.info("Returning response to webhook sender. - MainWebhookHandler")
        response = func.HttpResponse("Server error", status_code=500, headers={"Content-Type": "application/json"})
        logging.info(f"Response Status Code: {response.status_code}")
        logging.info(f"Response Headers: {response.headers}")
        logging.info(f"Response Body: {response.get_body()}")
        return response