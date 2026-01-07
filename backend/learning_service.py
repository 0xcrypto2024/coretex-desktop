import json
import logging
import asyncio
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class LearningService:
    def __init__(self, agent_instance, memory_manager, task_manager):
        self.agent = agent_instance
        self.memory_manager = memory_manager
        self.task_manager = task_manager
        from config import CONFIG_DIR
        self.state_file = CONFIG_DIR / "learning_state.json"
        
        # Incremental State
        self.last_ts = None
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.last_ts = data.get("last_processed_timestamp")
            except Exception as e:
                logger.error(f"Failed to load learning state: {e}")

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump({"last_processed_timestamp": self.last_ts}, f)
        except Exception as e:
            logger.error(f"Failed to save learning state: {e}")

    async def digest_context(self, batch_size=200):
        """
        Incremental Learning: Reads new audit logs and asks AI for broad context facts.
        """
        logger.info("Running Incremental Context Learning...")
        
        # 1. Fetch Audit Logs
        all_logs = await self.task_manager.get_audit_log(limit=1000) # Get deep history
        if not all_logs: 
            return

        # 2. Filter New Logs
        new_logs = []
        if not self.last_ts:
            new_logs = all_logs[:batch_size] # First run: take most recent batch_size
        else:
            for log in all_logs:
                if log['timestamp'] > self.last_ts:
                    new_logs.append(log)
            # Re-sort to chronological for coherent reading if needed, but reverse is fine for check
        
        if not new_logs:
            logger.info("No new logs to learn from.")
            return

        # Update TS to the most recent log in this batch (which is at index 0 because get_audit_log returns desc)
        most_recent_ts = new_logs[0]['timestamp']

        # limit batch size
        new_logs = new_logs[:batch_size]

        # 3. Format for AI
        history_text = "\n".join([f"[{l['timestamp']}] {l['sender']}: {l['text']}" for l in new_logs])
        
        # 4. Analyze
        facts = await self.agent.analyze_context_batch(history_text)
        
        # 5. Save Facts
        added_count = 0
        if facts:
            for fact in facts:
                if self.memory_manager.add_memory(fact):
                    added_count += 1
        
        logger.info(f"Context Learning Complete. Added {added_count} new facts.")
        
        # 6. Save State
        self.last_ts = most_recent_ts
        self._save_state()

    async def learn_from_feedback(self):
        """
        Targeted Correction: Learns from Audit vs Task discrepancies.
        """
        logger.info("Running Feedback Learning Loop...")
        # TODO: This requires deeper integration with TaskManager to get Rejected tasks
        # For now, let's implement the structure
        pass 

    async def start_scheduler(self):
        """Background loop."""
        # Wait 30s on startup to let system stabilize and finish catch-up
        await asyncio.sleep(30)
        logger.info("Learning Service Scheduler Started.")
        while True:
            try:
                await self.digest_context()
                # await self.learn_from_feedback()
                
                # Sleep 6 hours
                await asyncio.sleep(6 * 3600)
            except asyncio.CancelledError:
                logger.info("Learning Scheduler stopped.")
                break
            except Exception as e:
                logger.error(f"Learning Scheduler Error: {e}")
                await asyncio.sleep(600) # Retry after 10 mins
