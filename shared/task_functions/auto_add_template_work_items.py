# from services.karbon_services import Entities
import json
import re

# function to add work to each Karbon user
def add_work_to_karbon_user(karbon_users, work_template_key, work_title, work_due_date):
    return

# function to get every karbon user and their roles


# Function to extract and filter work templates with "AutoStartFromTemplate"
def extract_autostart_templates(api_data):
    templates_with_autostart = []

    for work_template in api_data.get("value", []):
        description = work_template.get("Description", "")

        # Extract JSON content from JSON_START to JSON_END
        match = re.search(r'JSON_START\s*(\{.*?\})\s*JSON_END', description, re.DOTALL)

        if match:
            json_str = match.group(1).strip()

            try:
                json_data = json.loads(json_str)  # Convert JSON string to dictionary
                
                # Check if "AutoStartFromTemplate" exists
                if "AUTOMATIONS" in json_data and "AutoStartFromTemplate" in json_data["AUTOMATIONS"]:
                    templates_with_autostart.append({
                        "WorkTemplateKey": work_template["WorkTemplateKey"],  # Key as a value
                        "Title": work_template["Title"],
                        "AutoStartFromTemplate": json_data["AUTOMATIONS"]["AutoStartFromTemplate"]
                    })
            
            except json.JSONDecodeError as e:
                print(f"Invalid JSON format in template: {work_template.get('Title', 'Unknown')}. Error: {e}")

    return templates_with_autostart
