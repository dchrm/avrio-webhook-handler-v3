import logging
from handlers.karbon_work_item_handler import handle_null_work, environment_variables

# Set up logging to print to console
logging.basicConfig(level=logging.INFO)

# Mock data to simulate a work item detail
work_item_details = {
    'Title': 'Sample Work Item',
    'WorkItemKey': 'sample_key',
    'AssigneeEmailAddress': 'assignee@example.com'
}
karbon_bearer_token = "sample_token"
karbon_access_key = "sample_access_key"

# Call the function to handle null work
handle_null_work(work_item_details, karbon_bearer_token, karbon_access_key)

# Print out the loaded environment variables to verify
print(environment_variables)
