
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AutoSessionManager:
    """
    Manages short-lived interactive sessions for auto-replies.
    State is kept in memory.
    """
    def __init__(self, timeout_minutes=10, max_turns=10):
        self.sessions = {} # { chat_id: { "start_time": dt, "last_msg_time": dt, "buffer": [], "turns": 0 } }
        self.timeout_minutes = timeout_minutes
        self.max_turns = max_turns

    def start_session(self, chat_id, initial_user_msg=None, initial_reply=None):
        """Starts a new session."""
        self.sessions[chat_id] = {
            "start_time": datetime.now(),
            "last_msg_time": datetime.now(),
            "buffer": [],
            "turns": 0
        }
        if initial_user_msg:
            self.sessions[chat_id]["buffer"].append({"role": "user", "content": initial_user_msg})
        if initial_reply:
            self.sessions[chat_id]["buffer"].append({"role": "agent", "content": initial_reply})
            
        logger.info(f"Started Auto-Reply Session for chat {chat_id}")

    def is_active(self, chat_id):
        """Checks if a session exists and isn't timed out."""
        if chat_id not in self.sessions:
            return False
            
        session = self.sessions[chat_id]
        
        # Check Timeout
        if datetime.now() - session["last_msg_time"] > timedelta(minutes=self.timeout_minutes):
            logger.info(f"Session {chat_id} timed out.")
            self.close_session(chat_id)
            return False
            
        # Check Max Turns
        if session["turns"] >= self.max_turns:
            logger.info(f"Session {chat_id} reached max turns.")
             # We don't close immediately here, we let the caller decide to summarize
            return True 
            
        return True

    def add_message(self, chat_id, role, content):
        """Adds a message to the session buffer."""
        if not self.is_active(chat_id): return
        
        self.sessions[chat_id]["buffer"].append({"role": role, "content": content})
        self.sessions[chat_id]["last_msg_time"] = datetime.now()
        
        if role == "agent":
            self.sessions[chat_id]["turns"] += 1

    def get_history(self, chat_id):
        """Returns the conversation history text."""
        if chat_id not in self.sessions: return ""
        
        text = ""
        for msg in self.sessions[chat_id]["buffer"]:
            role = "Me (Agent)" if msg['role'] == "agent" else "User"
            text += f"{role}: {msg['content']}\n"
        return text

    def close_session(self, chat_id):
        """Removes session from memory."""
        if chat_id in self.sessions:
            del self.sessions[chat_id]
            
    def get_buffer(self, chat_id):
        if chat_id in self.sessions:
            return self.sessions[chat_id]["buffer"]
        return []
