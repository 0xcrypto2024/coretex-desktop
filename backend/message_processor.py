import logging
from datetime import datetime
from typing import Dict, Any, Optional

from interfaces import TaskService

logger = logging.getLogger(__name__)

class MessageProcessor:
    def __init__(self, agent: Any, task_service: TaskService, memory_manager: Any, auto_session_manager: Any):
        self.agent = agent
        self.task_service = task_service
        self.memory_manager = memory_manager
        self.auto_session_manager = auto_session_manager

    def should_reply(
        self,
        analysis: Dict[str, Any],
        is_auto_reply_enabled: bool,
        is_working_hours: bool,
        is_self: bool
    ) -> bool:
        """Determines if the agent should auto-reply."""
        reply_text = analysis.get('reply_text')
        priority = int(analysis.get('priority', 4))
        action_required = analysis.get('action_required', False)

        return (
            is_auto_reply_enabled
            and bool(reply_text)
            and len(reply_text) > 2
            and priority <= 3
            and not is_self
            and "task added" not in reply_text.lower()
            and "okay" != reply_text.lower().strip()
            and not is_working_hours
        )

    async def process_message(
        self,
        message_data: Dict[str, Any],
        history_text: str,
        my_name: str,
        user_preferences: Optional[Dict] = None,
        recent_tasks: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates the analysis of a message.
        Returns a dict with analysis results and actions to take.
        """
        sender = message_data.get('sender', 'Unknown')
        text = message_data.get('text', '')
        
        # 1. Build Context
        memory_text = ""
        if recent_tasks:
            memory_text += "Recent Finished Tasks:\n" + "\n".join([f"- {t['summary']}" for t in recent_tasks])
        
        if user_preferences:
             memory_text += "\n\nUser Preferences (Learning):\n"
             memory_text += "ACCEPTED Tasks:\n" + "\n".join([f"- [P{t['priority']}] {t['summary']} (from {t['sender']}) " + (f"| Note: {', '.join(t['comments'])}" if t['comments'] else "") for t in user_preferences.get('accepted', [])])
             memory_text += "\nREJECTED Tasks:\n" + "\n".join([f"- [P{t['priority']}] {t['summary']} (from {t['sender']}) " + (f"| Note: {', '.join(t['comments'])}" if t['comments'] else "") for t in user_preferences.get('rejected', [])])

        # Long-term memory
        if self.memory_manager:
            memory_text += "\n\n" + self.memory_manager.get_memories_text()

        # 2. Analyze
        logger.info(f"Sending to Agent for analysis (Model: {self.agent.model_name})...")
        analysis = await self.agent.analyze_message(history_text, sender, my_name, memory_text)
        
        if not isinstance(analysis, dict):
            logger.error(f"Analysis format error: {analysis}")
            analysis = {"priority": 4, "summary": "Analysis format error", "action_required": False}

        return analysis
