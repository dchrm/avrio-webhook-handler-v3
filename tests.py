# example of how to use the function
from shared.task_functions.cascade_work import main as func
import json
from shared.services.karbon_services import Entities
import logging
import os
from dotenv import load_dotenv

load_dotenv()

test_work_item_key = "4rwWDy3GbvXr"

test_data = Entities(os.environ['KARBON_BEARER_TOKEN'], os.environ['KARBON_ACCESS_KEY']).get(f"WorkItems/{test_work_item_key}")

func(test_data)