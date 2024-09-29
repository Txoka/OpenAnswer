import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_SEARCH_API_KEY = os.getenv('GOOGLE_SEARCH_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Search Engine ID
SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID', "f2ae843af52fb4ff3")

# OpenAI Models
SEARCH_MODEL = os.getenv('SEARCH_MODEL', "gpt-4o-mini")
EXTRACT_MODEL = os.getenv('EXTRACT_MODEL', "gpt-4o-mini")
ANSWER_MODEL = os.getenv('ANSWER_MODEL', "gpt-4o-mini")

# Crawler settings
MAX_URLS = int(os.getenv('MAX_URLS', 5))
CRAWL_TIMEOUT = int(os.getenv('CRAWL_TIMEOUT', 30))

# API settings
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 8000))