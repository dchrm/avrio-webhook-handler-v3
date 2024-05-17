from utils.logging_config import setup_logging
import logging

# apply logging config file
setup_logging()

def contacts_handler(data, karbon_bearer_token, karbon_access_key):
    logging.info("Someone called the contacts handler, but it's not working yet.")