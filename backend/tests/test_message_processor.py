import pytest
from unittest.mock import AsyncMock, MagicMock
from message_processor import MessageProcessor

@pytest.fixture
def processor():
    return MessageProcessor(
        agent=AsyncMock(),
        task_service=AsyncMock(),
        memory_manager=MagicMock(),
        auto_session_manager=MagicMock()
    )

def test_should_reply_happy_path(processor):
    analysis = {
        "reply_text": "Sure, I will do that.",
        "priority": 2,
        "action_required": True
    }
    
    result = processor.should_reply(
        analysis=analysis,
        is_auto_reply_enabled=True,
        is_working_hours=False,
        is_self=False
    )
    
    assert result is True

def test_should_reply_working_hours(processor):
    analysis = {
        "reply_text": "Sure.",
        "priority": 2,
        "action_required": True
    }
    # Should not reply during working hours
    result = processor.should_reply(
        analysis, True, True, False 
    )
    assert result is False

def test_should_reply_low_priority(processor):
    analysis = {
        "reply_text": "Interesting.",
        "priority": 4, # Just info
        "action_required": False
    }
    result = processor.should_reply(
        analysis, True, False, False
    )
    assert result is False

@pytest.mark.asyncio
async def test_process_message_calls_agent(processor):
    # Arrange
    msg_data = {"sender": "Bob", "text": "Do this"}
    processor.agent.model_name = "GPT-4"
    processor.agent.analyze_message.return_value = {"summary": "Task", "priority": 1}
    processor.memory_manager.get_memories_text.return_value = "MemoryContext"
    
    # Act
    result = await processor.process_message(msg_data, "History", "BotName")
    
    # Assert
    assert result["summary"] == "Task"
    processor.agent.analyze_message.assert_called_once()
    
    # Check if memory was passed
    call_args = processor.agent.analyze_message.call_args
    assert "MemoryContext" in call_args[0][3]
