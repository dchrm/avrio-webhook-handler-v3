import azure.functions as func
import logging
import os
from handlers.karbon_work_item_handler import work_item_handler
from handlers.karbon_notes_handler import notes_handler
from handlers.karbon_contacts_handler import contacts_handler
from shared.services.karbon_services import is_karbon_webhook
from shared.task_functions.auto_add_template_work_items import add_work_to_karbon_user as auto_work
import asyncio

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Karbon webhook handler
@app.route(route="MainWebhookHandler", methods=['POST'])
async def MainWebhookHandler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("function_app.py: Received a request.")

    try:
        # Log request details
        logging.info('function_app.py: Trying to send webhook to webhook_processor.')
        logging.info(f"Request Headers: {req.headers}")
        logging.info(f"Request Body: {req.get_body()}")

        # Start webhook processing asynchronously
        await webhook_processor(req)

        # Return the response immediately and log the response details
        logging.info("function_app.py: Returning response to webhook sender.")
        response = func.HttpResponse("Webhook accepted", status_code=202, headers={"Content-Type": "application/json"})
        logging.info(f"Response Status Code: {response.status_code}")
        logging.info(f"Response Headers: {response.headers}")
        logging.info(f"Response Body: {response.get_body()}")
        return response

    except Exception as e:
        logging.error(f"function_app.py: Exception in MainWebhookHandler: {str(e)}")
        logging.info("function_app.py: Returning response to webhook sender.")
        response = func.HttpResponse("Server error", status_code=500, headers={"Content-Type": "application/json"})
        logging.info(f"function_app.py: Response Status Code: {response.status_code}")
        logging.info(f"function_app.py: Response Headers: {response.headers}")
        logging.info(f"function_app.py: Response Body: {response.get_body()}")
        return response

async def webhook_processor(req) -> None:
    logging.info("function_app.py: Received a request to handle a webhook.")

    try:
        logging.info("function_app.py: Trying to load access keys and other environment variables.")
        # Get API keys and other environment variables
        karbon_access_key = os.getenv('KARBON_ACCESS_KEY')
        karbon_bearer_token = os.getenv('KARBON_BEARER_TOKEN')
        azure_logic_app_handler_url = os.getenv('AZURE_LOGIC_APP_HANDLER')
    except Exception as e:
        logging.error(f"function_app.py: Failed to load environment variables with error: {str(e)}")
        return

    # Log the request headers and body
    logging.info(f"Request Headers: {req.headers}")
    logging.info(f"Request Body: {req.get_body()}")

    # Parse the request body safely
    try:
        logging.info("function_app.py: Trying to get JSON body of request.")
        req_body = req.get_json()
        logging.info(f"function_app.py: Parsed Request Body: {req_body}")
    except ValueError:
        logging.error("function_app.py: Invalid JSON received.")
        return

    # Process the webhook if it's valid for Karbon
    logging.info("function_app.py: Checking to see if webhook is from Karbon.")
    if is_karbon_webhook(req_body):
        logging.info("function_app.py: Webhook appears to be from Karbon.")
    else:
        logging.info("function_app.py: Request did not qualify as a Karbon webhook.")
        return

    resource_type = req_body.get('ResourceType')
    logging.info(f"function_app.py: Handling {resource_type} event.")

    # Mapping of Karbon resource types to handler functions
    karbon_event_handlers = {
        'WorkItem': work_item_handler,
        'Contact': contacts_handler,
        'Note': notes_handler
    }

    if resource_type not in karbon_event_handlers:
        logging.warning(f"function_app.py: Received unhandled event type: {resource_type}")
        return

    # Execute the handler function associated with the resource type
    try:
        logging.info("function_app.py: Trying to send webhook to associated sub-handler.")
        handler_function = karbon_event_handlers[resource_type]
        handler_function(req_body, karbon_bearer_token, karbon_access_key)
        logging.info(f"function_app.py: {resource_type} event processed successfully.")
    except Exception as e:
        logging.error(f"function_app.py: Error processing the {resource_type} event: {str(e)}", exc_info=True)

# Uncomment and configure the scheduled job if needed
# @app.schedule(schedule="0 0 9 * * *")
# def scheduled_job(timer: func.TimerRequest) -> None:
#     """Run the scheduled job every day at 4:00 AM Eastern Time."""
#     logging.info("function_app.py: Scheduled job triggered.")
#     logging.info(f"function_app.py: Scheduled job ran at: {timer.past_due_time}")
#     logging.info(f"function_app.py: Scheduled job is due at: {timer.next}")
#     logging.info("function_app.py: Running scheduled job.")
#     # Run the scheduled job here
#     auto_work()
#     logging.info("function_app.py: Scheduled job completed successfully.")