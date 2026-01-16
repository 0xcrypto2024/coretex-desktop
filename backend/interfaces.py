from typing import List, Dict, Any, Protocol, Optional

class TaskService(Protocol):
    """Protocol for high-level task management operations used by the agent."""
        
    async def get_recent_done_tasks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves recently completed tasks."""
        ...

    async def get_preference_examples(self, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieves task preferences (accepted/rejected examples)."""
        ...
        
    async def log_audit(self, message_data: Dict[str, Any], evaluation: Dict[str, Any], task_created: bool, reply_action: str = "none") -> None:
        """Logs an audit entry."""
        ...

    async def add_task(self, priority: int, summary: str, sender: str, link: str, deadline: Optional[str] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """High level method to add a task with logic."""
        ...

    async def get_daily_briefing_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns top priority tasks for daily digest."""
        ...
