from utils.logging_config import setup_logging
import logging

# apply logging config file
setup_logging()

def notes_handler(data, karbon_bearer_token, karbon_access_key):
    logging.info("Someone called the notes handler, but it's not working yet.")