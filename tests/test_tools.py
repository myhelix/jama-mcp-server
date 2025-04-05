import pytest
from unittest.mock import MagicMock

# Import the tool functions we want to test
from jama_mcp_server.server import (
    get_jama_projects,
    get_jama_item,
    get_jama_project_items
)

# --- Test Fixtures ---

@pytest.fixture
def mock_jama_client():
    """Provides a basic mock JamaClient instance."""
    return MagicMock()

@pytest.fixture
def mock_context(mock_jama_client):
    """Provides a simplified mock MCP Context containing the mock JamaClient."""
    mock_ctx = MagicMock()
    # Simulate the structure the tool function expects to find the client
    mock_ctx.request_context.lifespan_context = {"jama_client": mock_jama_client}
    return mock_ctx

# --- Tool Tests for get_jama_projects ---

@pytest.mark.asyncio
async def test_get_jama_projects_success(mock_context, mock_jama_client):
    """Test get_jama_projects returns data from mock client."""
    # Arrange: Configure the mock client's method
    mock_projects_data = [{"id": 1, "name": "Proj A"}, {"id": 2, "name": "Proj B"}]
    mock_jama_client.get_projects.return_value = mock_projects_data

    # Act: Call the tool function
    result = await get_jama_projects(mock_context)

    # Assert: Check the return value and that the mock was called
    assert result == mock_projects_data
    mock_jama_client.get_projects.assert_called_once()

@pytest.mark.asyncio
async def test_get_jama_projects_empty(mock_context, mock_jama_client):
    """Test get_jama_projects returns empty list when client does."""
    # Arrange
    mock_jama_client.get_projects.return_value = []

    # Act
    result = await get_jama_projects(mock_context)

    # Assert
    assert result == []
    mock_jama_client.get_projects.assert_called_once()

@pytest.mark.asyncio
async def test_get_jama_projects_error(mock_context, mock_jama_client):
    """Test get_jama_projects propagates exceptions from the client."""
    # Arrange: Configure the mock client to raise an error
    mock_jama_client.get_projects.side_effect = ConnectionError("API unavailable")

    # Act & Assert: Check that the exception is raised
    with pytest.raises(ConnectionError, match="API unavailable"):
        await get_jama_projects(mock_context)

    # Assert: Check the mock was still called
    mock_jama_client.get_projects.assert_called_once()
# --- Tool Tests for get_jama_item ---

@pytest.mark.asyncio
async def test_get_jama_item_success(mock_context, mock_jama_client):
    """Test get_jama_item returns data for a specific ID."""
    # Arrange
    item_id_to_test = "123"
    mock_item_data = {"id": 123, "name": "Item 123"}
    mock_jama_client.get_item.return_value = mock_item_data

    # Act
    result = await get_jama_item(item_id=item_id_to_test, ctx=mock_context)

    # Assert
    assert result == mock_item_data
    mock_jama_client.get_item.assert_called_once_with(item_id_to_test)

@pytest.mark.asyncio
async def test_get_jama_item_not_found(mock_context, mock_jama_client):
    """Test get_jama_item returns None when client returns None."""
    # Arrange
    item_id_to_test = "999"
    mock_jama_client.get_item.return_value = None # Simulate client returning None

    # Act
    result = await get_jama_item(item_id=item_id_to_test, ctx=mock_context)

    # Assert
    assert result is None
    mock_jama_client.get_item.assert_called_once_with(item_id_to_test)

@pytest.mark.asyncio
async def test_get_jama_item_error(mock_context, mock_jama_client):
    """Test get_jama_item propagates exceptions from the client."""
    # Arrange
    item_id_to_test = "123"
    mock_jama_client.get_item.side_effect = TimeoutError("Request timed out")

    # Act & Assert
    with pytest.raises(TimeoutError, match="Request timed out"):
        await get_jama_item(item_id=item_id_to_test, ctx=mock_context)

    # Assert
    mock_jama_client.get_item.assert_called_once_with(item_id_to_test)


# --- Tool Tests for get_jama_project_items ---

@pytest.mark.asyncio
async def test_get_jama_project_items_success(mock_context, mock_jama_client):
    """Test get_jama_project_items returns items for a project."""
    # Arrange
    project_id_to_test = "1"
    mock_items_data = [{"id": 10, "name": "Item A"}, {"id": 11, "name": "Item B"}]
    mock_jama_client.get_items.return_value = mock_items_data

    # Act
    result = await get_jama_project_items(project_id=project_id_to_test, ctx=mock_context)

    # Assert
    assert result == mock_items_data
    mock_jama_client.get_items.assert_called_once_with(project_id=project_id_to_test)

@pytest.mark.asyncio
async def test_get_jama_project_items_empty(mock_context, mock_jama_client):
    """Test get_jama_project_items returns empty list when client does."""
    # Arrange
    project_id_to_test = "2"
    mock_jama_client.get_items.return_value = [] # Simulate empty list from client

    # Act
    result = await get_jama_project_items(project_id=project_id_to_test, ctx=mock_context)

    # Assert
    assert result == []
    mock_jama_client.get_items.assert_called_once_with(project_id=project_id_to_test)

@pytest.mark.asyncio
async def test_get_jama_project_items_error(mock_context, mock_jama_client):
    """Test get_jama_project_items propagates exceptions from the client."""
    # Arrange
    project_id_to_test = "1"
    mock_jama_client.get_items.side_effect = ValueError("Invalid Project ID format")

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid Project ID format"):
        await get_jama_project_items(project_id=project_id_to_test, ctx=mock_context)

    # Assert
    mock_jama_client.get_items.assert_called_once_with(project_id=project_id_to_test)