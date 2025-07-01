import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Optional, Dict, Any
import logging

from mcp.server.fastmcp import FastMCP, Context
from .auth import get_jama_credentials, CredentialsError

# Configure basic logging FIRST
logging.basicConfig(level=logging.INFO, format='%(asctime)s - SERVER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if we need the real client or can use a mock
MOCK_MODE = os.environ.get("JAMA_MOCK_MODE", "false").lower() == "true"

if MOCK_MODE:
    from .mock_client import MockJamaClient as JamaClient
    logger.info("Using MockJamaClient due to JAMA_MOCK_MODE=true")
else:
    try:
        from py_jama_rest_client.client import JamaClient # Import the real client
        logger.info("Using real py_jama_rest_client.client.JamaClient")
    except ImportError:
        logger.error("Failed to import real JamaClient. Is py-jama-rest-client installed?")
        # Exit or raise a more specific error if the real client is mandatory when not in mock mode
        raise

@asynccontextmanager
async def jama_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """
    Manages the JamaClient lifecycle, retrieving credentials using get_jama_credentials
    and instantiating the JamaClient.
    """
    if MOCK_MODE:
        logger.info("Jama Mock Mode enabled. Skipping real authentication.")
        try:
            mock_client = JamaClient() # Instantiate the mock client
            yield {"jama_client": mock_client}
        except Exception as e:
             logger.error(f"Failed to initialize MockJamaClient: {e}")
             raise
        finally:
             logger.info("Jama mock lifespan context manager exiting.")
        return # Exit the function here for mock mode

    # --- Real Authentication Logic (only runs if not MOCK_MODE) ---
    jama_url = os.environ.get("JAMA_URL")
    if not jama_url:
        logger.error("JAMA_URL environment variable not set. Cannot connect to Jama.")
        # Let the lifespan fail, preventing server start without URL
        raise ValueError("JAMA_URL environment variable is required.")

    jama_client = None
    try:
        # Get credentials using the dedicated function
        logger.info("Attempting to retrieve Jama credentials...")
        client_id, client_secret = get_jama_credentials() # This handles AWS/Env Var logic and raises errors
        logger.info("Successfully retrieved Jama credentials.")

        # Instantiate the client
        logger.info(f"Attempting OAuth authentication to Jama at {jama_url}")
        jama_client = JamaClient(host_domain=jama_url, credentials=(client_id, client_secret), oauth=True)
        logger.info(f"Successfully configured JamaClient.")


        yield {"jama_client": jama_client}

    except CredentialsError as e: # Catch specific credential errors from auth.py
        logger.error(f"Failed to obtain Jama credentials: {e}")
        raise # Re-raise to prevent server start
    except Exception as e: # Catch other potential errors (e.g., JamaClient init)
        logger.error(f"Failed during JamaClient initialization or credential retrieval: {e}")
        # Re-raise the exception to prevent the server from starting incorrectly
        raise
    finally:
        # No explicit cleanup needed for JamaClient based on its usage pattern
        logger.info("Jama lifespan context manager exiting.")


# Instantiate the FastMCP server with the lifespan manager
mcp = FastMCP(
    "Jama Connect Server",
    lifespan=jama_lifespan,
)

# --- Tool Implementations ---

@mcp.tool()
async def get_jama_projects(ctx: Context) -> list[dict]:
    """
    Retrieves a list of projects from Jama Connect.

    Returns:
        A list of dictionaries representing projects.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info("Executing get_jama_projects tool")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    # Let exceptions from the client propagate
    projects = jama_client.get_projects()
    return projects

@mcp.tool()
async def get_jama_item(item_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific item from Jama Connect by its ID.

    Args:
        item_id: The ID (as a string) of the Jama item to retrieve.

    Returns:
        A dictionary representing the item.

    Raises:
        APIException: If the item is not found or an error occurs.
    """
    logger.info(f"Executing get_jama_item tool for item_id: {item_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    item = jama_client.get_item(item_id)
    # Let the client raise ResourceNotFoundException if applicable
    if not item and MOCK_MODE: # Handle mock case explicitly if needed
        raise ValueError(f"Mock Item with ID {item_id} not found.")
    return item

@mcp.tool()
async def get_jama_project_items(project_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves a list of items for a specific project from Jama Connect.

    Args:
        project_id: The ID (as a string) of the Jama project.

    Returns:
        A list of dictionaries representing items in the project.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_project_items tool for project_id: {project_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    items = jama_client.get_items(project_id=project_id)
    return items if items else []

@mcp.tool()
async def get_jama_item_children(item_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves child items for a specific Jama item.

    Args:
        item_id: The ID (as a string) of the parent Jama item.

    Returns:
        A list of dictionaries representing child items.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_item_children tool for parent_id: {item_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    children = jama_client.get_item_children(item_id=item_id)
    return children if children else []

@mcp.tool()
async def get_jama_relationships(project_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves all relationships within a specific Jama project.

    Args:
        project_id: The ID (as a string) of the Jama project.

    Returns:
        A list of dictionaries representing relationships.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_relationships tool for project_id: {project_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    relationships = jama_client.get_relationships(project_id=project_id)
    return relationships if relationships else []

@mcp.tool()
async def get_jama_relationship(relationship_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific relationship by its ID.

    Args:
        relationship_id: The ID (as a string) of the relationship.

    Returns:
        A dictionary representing the relationship.

    Raises:
        APIException: If the relationship is not found or an error occurs.
    """
    logger.info(f"Executing get_jama_relationship tool for relationship_id: {relationship_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    relationship = jama_client.get_relationship(relationship_id=relationship_id)
    # Let py-jama-rest-client raise ResourceNotFoundException if applicable
    if not relationship and MOCK_MODE: # Handle mock case explicitly if needed
         raise ValueError(f"Mock Relationship with ID {relationship_id} not found.")
    return relationship

@mcp.tool()
async def get_jama_item_upstream_relationships(item_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves upstream relationships for a specific Jama item.

    Args:
        item_id: The ID (as a string) of the Jama item.

    Returns:
        A list of dictionaries representing upstream relationships.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_item_upstream_relationships tool for item_id: {item_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    relationships = jama_client.get_items_upstream_relationships(item_id=item_id)
    return relationships if relationships else []

@mcp.tool()
async def get_jama_item_downstream_relationships(item_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves downstream relationships for a specific Jama item.

    Args:
        item_id: The ID (as a string) of the Jama item.

    Returns:
        A list of dictionaries representing downstream relationships.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_item_downstream_relationships tool for item_id: {item_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    relationships = jama_client.get_items_downstream_relationships(item_id=item_id)
    return relationships if relationships else []

@mcp.tool()
async def get_jama_item_upstream_related(item_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves upstream related items for a specific Jama item.

    Args:
        item_id: The ID (as a string) of the Jama item.

    Returns:
        A list of dictionaries representing upstream related items.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_item_upstream_related tool for item_id: {item_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    items = jama_client.get_items_upstream_related(item_id=item_id)
    return items if items else []

@mcp.tool()
async def get_jama_item_downstream_related(item_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves downstream related items for a specific Jama item.

    Args:
        item_id: The ID (as a string) of the Jama item.

    Returns:
        A list of dictionaries representing downstream related items.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_item_downstream_related tool for item_id: {item_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    items = jama_client.get_items_downstream_related(item_id=item_id)
    return items if items else []

@mcp.tool()
async def get_jama_item_types(ctx: Context) -> list[dict]:
    """
    Retrieves all item types from Jama Connect.

    Returns:
        A list of dictionaries representing item types.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info("Executing get_jama_item_types tool")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    item_types = jama_client.get_item_types()
    return item_types if item_types else []

@mcp.tool()
async def get_jama_item_type(item_type_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific item type by its ID.

    Args:
        item_type_id: The ID (as a string) of the item type.

    Returns:
        A dictionary representing the item type.

    Raises:
        APIException: If the item type is not found or an error occurs.
    """
    logger.info(f"Executing get_jama_item_type tool for item_type_id: {item_type_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    item_type = jama_client.get_item_type(item_type_id=item_type_id)
    if not item_type and MOCK_MODE:
         raise ValueError(f"Mock Item type with ID {item_type_id} not found.")
    return item_type

@mcp.tool()
async def get_jama_pick_lists(ctx: Context) -> list[dict]:
    """
    Retrieves all pick lists from Jama Connect.

    Returns:
        A list of dictionaries representing pick lists.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info("Executing get_jama_pick_lists tool")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    pick_lists = jama_client.get_pick_lists()
    return pick_lists if pick_lists else []

@mcp.tool()
async def get_jama_pick_list(pick_list_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific pick list by its ID.

    Args:
        pick_list_id: The ID (as a string) of the pick list.

    Returns:
        A dictionary representing the pick list.

    Raises:
        APIException: If the pick list is not found or an error occurs.
    """
    logger.info(f"Executing get_jama_pick_list tool for pick_list_id: {pick_list_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    pick_list = jama_client.get_pick_list(pick_list_id=pick_list_id)
    if not pick_list and MOCK_MODE:
         raise ValueError(f"Mock Pick list with ID {pick_list_id} not found.")
    return pick_list

@mcp.tool()
async def get_jama_pick_list_options(pick_list_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves options for a specific pick list.

    Args:
        pick_list_id: The ID (as a string) of the pick list.

    Returns:
        A list of dictionaries representing pick list options.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_pick_list_options tool for pick_list_id: {pick_list_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    options = jama_client.get_pick_list_options(pick_list_id=pick_list_id)
    return options if options else []

@mcp.tool()
async def get_jama_pick_list_option(pick_list_option_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific pick list option by its ID.

    Args:
        pick_list_option_id: The ID (as a string) of the pick list option.

    Returns:
        A dictionary representing the pick list option.

    Raises:
        APIException: If the pick list option is not found or an error occurs.
    """
    logger.info(f"Executing get_jama_pick_list_option tool for pick_list_option_id: {pick_list_option_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    option = jama_client.get_pick_list_option(pick_list_option_id=pick_list_option_id)
    if not option and MOCK_MODE:
         raise ValueError(f"Mock Pick list option with ID {pick_list_option_id} not found.")
    return option

@mcp.tool()
async def get_jama_tags(project_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves all tags for a specific project.

    Args:
        project_id: The ID (as a string) of the Jama project.

    Returns:
        A list of dictionaries representing tags.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_tags tool for project_id: {project_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    tags = jama_client.get_tags(project=project_id) # Param name is 'project' in client
    return tags if tags else []

@mcp.tool()
async def get_jama_tagged_items(tag_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves items associated with a specific tag.

    Args:
        tag_id: The ID (as a string) of the tag.

    Returns:
        A list of dictionaries representing items associated with the tag.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_tagged_items tool for tag_id: {tag_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    items = jama_client.get_tagged_items(tag_id=tag_id)
    return items if items else []

@mcp.tool()
async def get_jama_test_cycle(test_cycle_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific test cycle by its ID.

    Args:
        test_cycle_id: The ID (as a string) of the test cycle.

    Returns:
        A dictionary representing the test cycle.

    Raises:
        APIException: If the test cycle is not found or an error occurs.
    """
    logger.info(f"Executing get_jama_test_cycle tool for test_cycle_id: {test_cycle_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    cycle = jama_client.get_test_cycle(test_cycle_id=test_cycle_id)
    if not cycle and MOCK_MODE:
         raise ValueError(f"Mock Test cycle with ID {test_cycle_id} not found.")
    return cycle

@mcp.tool()
async def get_jama_test_runs(test_cycle_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves test runs associated with a specific test cycle.

    Args:
        test_cycle_id: The ID (as a string) of the test cycle.

    Returns:
        A list of dictionaries representing test runs.

    Raises:
        APIException: If an error occurs during the Jama API call.
    """
    logger.info(f"Executing get_jama_test_runs tool for test_cycle_id: {test_cycle_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    runs = jama_client.get_testruns(test_cycle_id=test_cycle_id)
    return runs if runs else []

@mcp.tool()
async def create_item(
    project: int,
    item_type_id: int,
    child_item_type_id: int,
    location: dict,
    fields: dict,
    ctx: Context,
) -> dict:
    """
    Creates a new item in Jama Connect.
    Args:
        project: The ID of the project to create the item in.
        item_type_id: The ID of the item type for the new item.
        child_item_type_id: The ID of the child item type for the new item.
        location: A dictionary with parent ID, e.g. {"item": 123}
        fields: A dictionary of fields for the new item.
    Returns:
        A dictionary representing the newly created item.
    """
    logger.info(f"Executing create_item tool for project: {project}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    item_id = jama_client.post_item(
        project=project,
        item_type_id=item_type_id,
        child_item_type_id=child_item_type_id,
        location=location,
        fields=fields,
    )
    new_item = await get_jama_item(item_id=str(item_id), ctx=ctx)
    return new_item

@mcp.tool()
async def create_tag(name: str, project: int, ctx: Context) -> int:
    """
    Create a new tag in the project with the specified ID
    Args:
        name: The display name for the tag
        project: The project to create the new tag in
    Returns: The integer API ID fr the newly created Tag.
    """
    logger.info(f"Executing create_tag tool for project: {project}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    tag_id = jama_client.post_tag(name=name, project=project)
    return tag_id


@mcp.tool()
async def add_jama_item_tag(item_id: int, tag_id: int, ctx: Context) -> int:
    """
    Add an existing tag to the item with the specified ID
    Args:
        item_id: The API ID of the item to add a tag.
        tag_id: The API ID of the tag to add to the item.
    Returns: 201 if successful
    """
    logger.info(f"Executing add_jama_item_tag tool for item_id: {item_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    status_code = jama_client.post_item_tag(item_id=item_id, tag_id=tag_id)
    return status_code


@mcp.tool()
async def update_item(
    project: int,
    item_id: int,
    item_type_id: int,
    child_item_type_id: int,
    location: dict,
    fields: dict,
    ctx: Context,
) -> int:
    """
    This method will PUT a new item to Jama Connect.
    :param project integer representing the project to which this item is to be posted
    :param item_id integer representing the item which is to be updated
    :param item_type_id integer ID of an Item Type.
    :param child_item_type_id integer ID of an Item Type.
    :param location dictionary  with a key of 'item' or 'project' and an value with the ID of the parent
    :param fields dictionary item field data.
    :return integer ID of the successfully posted item or None if there was an error."""
    logger.info(f"Executing update_item tool for item_id: {item_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    response = jama_client.put_item(
        project=project,
        item_id=item_id,
        item_type_id=item_type_id,
        child_item_type_id=child_item_type_id,
        location=location,
        fields=fields,
    )
    return response

@mcp.tool()
async def create_project(
    name: str,
    project_key: str,
    item_type_id: int,
    ctx: Context,
) -> dict:
    """
    Creates a new project in Jama Connect.
    Args:
        name: The name of the project.
        project_key: The project key.
        item_type_id: The ID of the item type to use for the project.
    Returns:
        A dictionary representing the newly created project.
    """
    logger.info(f"Executing create_project tool for project: {name}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    project = jama_client.post_project(
        name=name,
        project_key=project_key,
        item_type_id=item_type_id,
    )
    return project

@mcp.tool()
async def create_relationship(
    from_item_id: int,
    to_item_id: int,
    ctx: Context,
) -> dict:
    """
    Creates a new relationship between two items in Jama Connect.
    Args:
        from_item_id: The ID of the item to create the relationship from.
        to_item_id: The ID of the item to create the relationship to.
    Returns:
        A dictionary representing the newly created relationship.
    """
    logger.info(f"Executing create_relationship tool for items: {from_item_id} -> {to_item_id}")
    jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
    relationship = jama_client.post_relationship(
        from_item=from_item_id,
        to_item=to_item_id,
    )
    return relationship

@mcp.tool()
async def test_jama_connection(ctx: Context) -> dict:
    """
    Tests the connection and authentication to the Jama Connect API.
    Attempts to fetch available API endpoints as a lightweight check.

    Returns:
        A dictionary containing the result of the get_available_endpoints call.

    Raises:
        APIException: If the connection test fails.
        ValueError: If the JamaClient is not found in the context.
    """
    logger.info("Executing test_jama_connection tool")
    jama_client: JamaClient = ctx.request_context.lifespan_context.get("jama_client")
    if not jama_client:
        raise ValueError("JamaClient not found in context for connection test.")

    # Attempt a simple API call to verify connection further
    # Let any exceptions propagate
    endpoints = jama_client.get_available_endpoints()
    return endpoints # Return the actual result or let exception indicate failure


def main():
    """Entry point for the jama-mcp-server script."""
    logger.info("Starting Jama MCP server...")

    if not MOCK_MODE and not os.environ.get("JAMA_URL"):
        logger.error("JAMA_URL environment variable is not set when not in MOCK_MODE.")
        print("\nERROR: JAMA_URL environment variable is not set.")
        print("Please set JAMA_URL and OAuth authentication variables (JAMA_CLIENT_ID, JAMA_CLIENT_SECRET),")
        print("or run in mock mode by setting JAMA_MOCK_MODE=true.")
        exit(1) # Exit if essential config is missing for non-mock mode

    # Run the MCP server (uses uvicorn defaults)
    mcp.run()

if __name__ == "__main__":
    # This allows running the server directly with `python -m jama_mcp_server.server`
    main()
