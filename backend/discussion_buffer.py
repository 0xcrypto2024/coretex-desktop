import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from config import CONFIG_DIR
ACTIVE_BUFFER_FILE = CONFIG_DIR / "discussions.json"
HISTORY_FILE = CONFIG_DIR / "daily_history.json"

class DiscussionBuffer:
    def __init__(self):
        self.buffer = self._load_buffer()
        self._ensure_history_file()

    def _load_buffer(self):
        """Loads active buffer from disk."""
        if os.path.exists(ACTIVE_BUFFER_FILE):
            try:
                with open(ACTIVE_BUFFER_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def _save_buffer(self):
        """Saves active buffer to disk."""
        with open(ACTIVE_BUFFER_FILE, "w") as f:
            json.dump(self.buffer, f, indent=2)

    def _ensure_history_file(self):
        """Ensures history file exists."""
        if not os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "w") as f:
                json.dump([], f)

    def add_point(self, chat_name: str, sender: str, summary: str):
        """Adds a discussion point to the buffer."""
        point = {
            "timestamp": datetime.now().isoformat(),
            "chat": chat_name,
            "sender": sender,
            "summary": summary
        }
        self.buffer.append(point)
        self._save_buffer()
        logger.info(f"Buffered discussion point from {sender} in {chat_name}")

    def get_all(self):
        """Returns all points in the active buffer."""
        return self.buffer

    def get_grouped_text(self):
        """Returns buffer content formatted for AI summarization."""
        if not self.buffer:
            return None
            
        text = "Here are the un-processed discussion points from today:\n\n"
        grouped = {}
        for p in self.buffer:
            chat = p['chat']
            if chat not in grouped: grouped[chat] = []
            grouped[chat].append(f"- [{p['sender']}]: {p['summary']}")
            
        for chat, points in grouped.items():
            text += f"### {chat}\n" + "\n".join(points) + "\n\n"
            
        return text

    def clear(self):
        """Clears the active buffer."""
        self.buffer = []
        self._save_buffer()

    def archive_daily_summary(self, summary_text):
        """Archives the generated summary to history."""
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "summary_text": summary_text,
            "point_count": len(self.buffer)
        }
        
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except:
            history = []
            
        history.insert(0, entry) # Newest first
        
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
            
        logger.info("Archived daily discussion summary.")

    def get_history(self):
        """Returns historical summaries."""
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
