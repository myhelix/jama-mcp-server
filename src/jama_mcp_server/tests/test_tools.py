import pytest
from unittest.mock import MagicMock

# Import the tool functions we want to test
from jama_mcp_server.server import (
    get_jama_projects,
    get_jama_item,
    get_jama_project_items,
    create_item,
    create_tag,
    add_jama_item_tag,
    update_item,
    create_project,
    create_relationship,
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


# --- Tool Tests for create_item ---
@pytest.mark.asyncio
async def test_create_item_success(mock_context, mock_jama_client):
    """Test create_item returns data from mock client."""
    # Arrange
    mock_item_data = {"id": 999, "name": "New Item"}
    mock_jama_client.post_item.return_value = 999
    mock_jama_client.get_item.return_value = mock_item_data

    # Act
    result = await create_item(
        project=1,
        item_type_id=10,
        child_item_type_id=10,
        location={"project": 1},
        fields={"name": "New Item", "description": "A new test item"},
        ctx=mock_context
    )

    # Assert
    assert result == mock_item_data
    mock_jama_client.post_item.assert_called_once()

# --- Tool Tests for create_tag ---

@pytest.mark.asyncio
async def test_create_tag_success(mock_context, mock_jama_client):
    """Test create_tag returns data from mock client."""
    # Arrange
    mock_tag_id = 999
    mock_jama_client.post_tag.return_value = mock_tag_id

    # Act
    result = await create_tag(
        name="New Tag",
        project=1,
        ctx=mock_context
    )

    # Assert
    assert result == mock_tag_id
    mock_jama_client.post_tag.assert_called_once()

# --- Tool Tests for add_jama_item_tag ---

@pytest.mark.asyncio
async def test_add_jama_item_tag_success(mock_context, mock_jama_client):
    """Test add_jama_item_tag returns data from mock client."""
    # Arrange
    mock_response = 201
    mock_jama_client.post_item_tag.return_value = mock_response

    # Act
    result = await add_jama_item_tag(
        item_id=123,
        tag_id=301,
        ctx=mock_context
    )

    # Assert
    assert result == mock_response
    mock_jama_client.post_item_tag.assert_called_once()

# --- Tool Tests for update_item ---

@pytest.mark.asyncio
async def test_update_item_success(mock_context, mock_jama_client):
    """Test update_item returns data from mock client."""
    # Arrange
    mock_response = {"status": "success"}
    mock_jama_client.put_item.return_value = mock_response

    # Act
    result = await update_item(
        project=1,
        item_id=123,
        item_type_id=10,
        child_item_type_id=10,
        location={"project": 1},
        fields={"name": "Updated Name"},
        ctx=mock_context
    )

    # Assert
    assert result == mock_response
    mock_jama_client.put_item.assert_called_once()

# --- Tool Tests for create_project ---

@pytest.mark.asyncio
async def test_create_project_success(mock_context, mock_jama_client):
    """Test create_project returns data from mock client."""
    # Arrange
    mock_project_data = {"id": 777, "name": "New Project"}
    mock_jama_client.post_project.return_value = mock_project_data

    # Act
    result = await create_project(
        name="New Project",
        project_key="NP",
        item_type_id=10,
        ctx=mock_context
    )

    # Assert
    assert result == mock_project_data
    mock_jama_client.post_project.assert_called_once()

# --- Tool Tests for create_relationship ---

@pytest.mark.asyncio
async def test_create_relationship_success(mock_context, mock_jama_client):
    """Test create_relationship returns data from mock client."""
    # Arrange
    mock_relationship_data = {"id": 666, "fromItem": 123, "toItem": 456}
    mock_jama_client.post_relationship.return_value = mock_relationship_data

    # Act
    result = await create_relationship(
        from_item_id=123,
        to_item_id=456,
        ctx=mock_context
    )

    # Assert
    assert result == mock_relationship_data
    mock_jama_client.post_relationship.assert_called_once()