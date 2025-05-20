import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Available languages for EasyOCR with script groups
AVAILABLE_LANGUAGES = {
    "English": {"code": "en", "script": "latin"},
    "Chinese (Traditional)": {"code": "ch_tra", "script": "chinese"},
    "Japanese": {"code": "ja", "script": "japanese"},
    "Korean": {"code": "ko", "script": "korean"},
    "French": {"code": "fr", "script": "latin"},
    "German": {"code": "de", "script": "latin"},
}