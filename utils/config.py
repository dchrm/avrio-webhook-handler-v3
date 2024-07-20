import os

BASE_URL = os.environ.get('KARBON_API_BASE_URL', 'https://api.karbonhq.com/v3')
DEFAULT_AUTHOR_EMAIL = os.environ.get('DEFAULT_AUTHOR_EMAIL', 'karbonbot@avriopro.com')

# AskNicely settings
ask_nicely_minutes_delay=1440