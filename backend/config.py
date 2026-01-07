import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load Env (Dev Mode)
load_dotenv()

# desktop Config Path
CONFIG_DIR = Path.home() / ".cortex"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

data = load_config()

def get_conf(key, default=None):
    return data.get(key) or os.getenv(key, default)

# Telegram Credentials
API_ID = get_conf("API_ID")
API_HASH = get_conf("API_HASH")
SESSION_STRING = get_conf("SESSION_STRING")
GROUP_TRIGGER_KEYWORDS = get_conf("GROUP_TRIGGER_KEYWORDS") or ["everyone", "all", "here", "channel", "@everyone", "@all"]

# Google AI
GENAI_KEY = get_conf("GENAI_KEY")

# Notion Config
NOTION_TOKEN = get_conf("NOTION_TOKEN")
NOTION_DATABASE_ID = get_conf("NOTION_DATABASE_ID")

# Feature Toggles
ENABLE_AUTO_REPLY = str(get_conf("ENABLE_AUTO_REPLY", "true")).lower() == "true"
WORKING_HOURS_START = int(get_conf("WORKING_HOURS_START", "9"))
WORKING_HOURS_END = int(get_conf("WORKING_HOURS_END", "18"))

# Long-term Memory Config
ENABLE_LONG_TERM_MEMORY = str(get_conf("ENABLE_LONG_TERM_MEMORY", "true")).lower() == "true"
MEMORY_FILE_PATH = str(CONFIG_DIR / "memory.json")

# Startup Catch-Unique
CATCH_UP_SECONDS = int(get_conf("CATCH_UP_SECONDS", "120"))

def get_dynamic_conf():
    """Reloads config from disk to get latest values."""
    return load_config()

def is_auto_reply_enabled():
    """Checks if auto-reply is valid dynamically."""
    conf = get_dynamic_conf()
    val = conf.get("ENABLE_AUTO_REPLY", os.getenv("ENABLE_AUTO_REPLY", "true"))
    return str(val).lower() == "true"
