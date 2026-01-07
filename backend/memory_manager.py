import json
import logging
import os

from config import MEMORY_FILE_PATH

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, storage_file=None):
        self.storage_file = storage_file or MEMORY_FILE_PATH
        self.memories = self._load_memories()

    def _load_memories(self):
        if not os.path.exists(self.storage_file):
            return []
        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
                return data.get("facts", [])
        except Exception as e:
            logger.error(f"Failed to load memories: {e}")
            return []

    def _save_memories(self):
        try:
            with open(self.storage_file, 'w') as f:
                json.dump({"facts": self.memories}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")

    def add_memory(self, fact: str):
        """Adds a new fact if it doesn't already exist."""
        if not fact or not isinstance(fact, str): return False
        
        # Deduplication (Simple exact match)
        if fact in self.memories:
            logger.info(f"Memory already exists: {fact}")
            return False
            
        self.memories.append(fact)
        self._save_memories()
        logger.info(f"Memory saved: {fact}")
        return True

    def get_memories_text(self):
        """Returns a formatted string of memories for the prompt."""
        if not self.memories:
            return "No long-term memories yet."
        
        return "Long-term Memory (Facts):" + "".join([f"\n- {m}" for m in self.memories])
