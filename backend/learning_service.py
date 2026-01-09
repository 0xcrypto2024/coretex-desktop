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
        self.last_feedback_ts = None # Track rejected task processing
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.last_ts = data.get("last_processed_timestamp")
                    self.last_feedback_ts = data.get("last_feedback_timestamp")
            except Exception as e:
                logger.error(f"Failed to load learning state: {e}")

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    "last_processed_timestamp": self.last_ts,
                    "last_feedback_timestamp": self.last_feedback_ts
                }, f)
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
        Targeted Correction: Learns from Rejected tasks with comments.
        """
        logger.info("Running Feedback Learning Loop...")
        
        # 1. Fetch Rejected Tasks with Comments
        rejected_tasks = await self.task_manager.get_rejected_tasks_with_comments(limit=50)
        
        if not rejected_tasks:
            logger.info("No rejected tasks with comments found.")
            return

        # 2. Filter New Rejections (Naive implementation: Check if we processed this specific batch?)
        # Since we don't have timestamps on tasks easily in the compact returned dict, we'll try to rely 
        # on the content or just process. 
        # Better: Filter by comments that we haven't seen? 
        # For MVP: We will process everything but rely on MemoryManager deduplication.
        # Ideally, we should store IDs of processed tasks. 
        # Let's assume we can re-process safely because 'add_memory' is idempotent for exact string matches.
        # But if the AI generates different strings, we get dupes. 
        # Let's filter by checking if any 'new' tasks exist?
        # Actually, let's just process. The cost is low (periodic).
        
        # 3. Format for AI
        feedback_text = ""
        count = 0
        for t in rejected_tasks:
            feedback_text += f"- Task: {t['summary']}\n  Comments: {', '.join(t['comments'])}\n"
            count += 1
            
        if not feedback_text:
            return

        # 4. Analyze
        rules = await self.agent.analyze_feedback_batch(feedback_text)
        
        # 5. Save Rules
        added_count = 0
        if rules:
            for rule in rules:
                if self.memory_manager.add_memory(rule):
                    added_count += 1
                    
        logger.info(f"Feedback Learning Complete. Processed {count} tasks. Learned {added_count} new rules.")
        
        # Update timestamp if we had one (Using current time as a proxy for 'run time')
        self.last_feedback_ts = datetime.now().isoformat()
        self._save_state()
        
        # Trigger Consolidation if needed
        await self.memory_manager.consolidate_memories(self.agent)

    async def start_scheduler(self):
        """Background loop."""
        # Wait 30s on startup to let system stabilize and finish catch-up
        await asyncio.sleep(30)
        logger.info("Learning Service Scheduler Started.")
        while True:
            try:
                await self.digest_context()
                await self.learn_from_feedback()
                
                # Sleep 6 hours
                await asyncio.sleep(6 * 3600)
            except asyncio.CancelledError:
                logger.info("Learning Scheduler stopped.")
                break
            except Exception as e:
                logger.error(f"Learning Scheduler Error: {e}")
                await asyncio.sleep(600) # Retry after 10 mins
