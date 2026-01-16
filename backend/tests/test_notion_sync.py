import pytest
from unittest.mock import AsyncMock, MagicMock
from notion_sync import NotionSync

@pytest.mark.asyncio
async def test_create_task_page_success():
    # Arrange
    mock_client = AsyncMock()
    mock_client.pages.create.return_value = {"id": "test-page-id"}
    
    sync = NotionSync(client=mock_client)
    task = {
        "summary": "Test Task",
        "priority": 1,
        "sender": "Alice",
        "link": "http://example.com"
    }

    # Act
    page_id = await sync.create_task_page(task)

    # Assert
    assert page_id == "test-page-id"
    mock_client.pages.create.assert_called_once()
    
    # Verify properties
    call_args = mock_client.pages.create.call_args[1]
    assert call_args['properties']['Name']['title'][0]['text']['content'] == "Test Task"
    assert call_args['properties']['Link']['url'] == "http://example.com"

@pytest.mark.asyncio
async def test_find_task_by_link_cached():
    # Arrange
    mock_client = AsyncMock()
    sync = NotionSync(client=mock_client)
    
    link = "http://example.com/check"
    sync._seen_links.add(link) # Simulate cache

    # Act
    result = await sync.find_task_by_link(link)

    # Assert
    assert result == "cached-duplicate"
    mock_client.search.assert_not_called()

@pytest.mark.asyncio
async def test_find_task_by_link_remote_hit():
    # Arrange
    mock_client = AsyncMock()
    sync = NotionSync(client=mock_client)
    link = "http://example.com/remote"
    
    # Mock search return
    mock_client.search.return_value = {
        "results": [
            {
                "id": "found-id",
                "properties": {
                    "Link": {"url": link}
                }
            }
        ]
    }

    # Act
    result = await sync.find_task_by_link(link)

    # Assert
    assert result == "found-id"
    mock_client.search.assert_called_once()
    assert link in sync._seen_links # Should cache it
