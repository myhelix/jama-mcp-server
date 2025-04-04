import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

from mcp.server.fastmcp import FastMCP, Context

# Configure basic logging FIRST
logging.basicConfig(level=logging.INFO, format='%(asctime)s - SERVER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if we need the real client or can use a mock
MOCK_MODE = os.environ.get("JAMA_MOCK_MODE", "false").lower() == "true"

if MOCK_MODE:
    from mock_client import MockJamaClient as JamaClient # Import the mock
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
    Manages the JamaClient lifecycle, handling authentication based on environment variables.
    Prioritizes OAuth 2.0, falls back to Basic Auth.
    """
    if MOCK_MODE:
        logger.info("Jama Mock Mode enabled. Skipping real authentication.")
        try:
            mock_client = JamaClient() # Instantiate the mock client
            yield {"jama_client": mock_client}
        except Exception as e:
             logger.error(f"Failed to initialize MockJamaClient: {e}", exc_info=True)
             raise
        finally:
             logger.info("Jama mock lifespan context manager exiting.")
        return # Exit the function here for mock mode

    # --- Real Authentication Logic (only runs if not MOCK_MODE) ---
    jama_url = os.environ.get("JAMA_URL")
    client_id = os.environ.get("JAMA_CLIENT_ID")
    client_secret = os.environ.get("JAMA_CLIENT_SECRET")
    username = os.environ.get("JAMA_USER")
    password = os.environ.get("JAMA_PASSWORD")

    if not jama_url:
        logger.error("JAMA_URL environment variable not set. Cannot connect to Jama.")
        raise ValueError("JAMA_URL environment variable is required.")

    jama_client = None
    auth_method = None

    try:
        if client_id and client_secret:
            logger.info(f"Attempting OAuth authentication to Jama at {jama_url}")
            # Note: py-jama-rest-client uses client_id/secret directly in constructor for OAuth
            jama_client = JamaClient(host_domain=jama_url, client_id=client_id, client_secret=client_secret)
            auth_method = "OAuth 2.0"
        elif username and password:
            logger.info(f"Attempting Basic authentication to Jama at {jama_url}")
            jama_client = JamaClient(host_domain=jama_url, credentials=(username, password))
            auth_method = "Basic Auth"
        else:
            logger.error("Missing required Jama authentication environment variables. "
                         "Set either (JAMA_CLIENT_ID, JAMA_CLIENT_SECRET) for OAuth "
                         "or (JAMA_USER, JAMA_PASSWORD) for Basic Auth.")
            raise ValueError("Missing Jama authentication credentials in environment variables.")

        # Optional: Add a simple check to confirm connection/authentication if the client library supports it easily.
        # For now, we assume instantiation implies potential connectivity.
        # e.g., try jama_client.get_available_endpoints() or get_current_user() if not excluded
        logger.info(f"Successfully configured JamaClient using {auth_method}.")

        yield {"jama_client": jama_client}

    except Exception as e:
        logger.error(f"Failed to initialize JamaClient: {e}", exc_info=True)
        # Re-raise the exception to prevent the server from starting incorrectly
        raise
    finally:
        # No explicit cleanup needed for JamaClient based on its usage pattern
        logger.info("Jama lifespan context manager exiting.")


# Instantiate the FastMCP server with the lifespan manager
mcp = FastMCP(
    "Jama Connect Server",
    lifespan=jama_lifespan,
    # Add dependencies required by py-jama-rest-client if needed for deployment packaging
    # dependencies=["requests"] # py-jama-rest-client likely brings this in
)

# --- Tool Implementations ---

@mcp.tool()
async def get_jama_projects(ctx: Context) -> list[dict]:
    """
    Retrieves a list of projects from Jama Connect.
    """
    logger.info("Executing get_jama_projects tool")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        # The py_jama_rest_client's get_projects method handles pagination internally
        projects = jama_client.get_projects()
        logger.info(f"Retrieved {len(projects)} projects.")
        # Ensure the return type is suitable for MCP (usually list of dicts)
        return projects
    except Exception as e:
        logger.error(f"Error in get_jama_projects tool: {e}", exc_info=True)
        # Return a dictionary indicating the error, as tools should return results
        return {"error": f"Failed to retrieve Jama projects: {str(e)}"}

@mcp.tool()
async def get_jama_item(item_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific item from Jama Connect by its ID.

    Args:
        item_id: The ID (as a string) of the Jama item to retrieve.
    """
    logger.info(f"Executing get_jama_item tool for item_id: {item_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        item = jama_client.get_item(item_id)
        logger.info(f"Retrieved item {item_id}.")
        if not item:
             return {"error": f"Item with ID {item_id} not found."}
        return item
    except Exception as e:
        logger.error(f"Error in get_jama_item tool for item_id {item_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve Jama item {item_id}: {str(e)}"}

@mcp.tool()
async def get_jama_project_items(project_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves a list of items for a specific project from Jama Connect.

    Args:
        project_id: The ID (as a string) of the Jama project.
    """
    logger.info(f"Executing get_jama_project_items tool for project_id: {project_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        # The py_jama_rest_client's get_items method handles pagination internally when called with project ID
        # The underlying client handles string conversion if needed, pass the string directly.
        # The get_items method expects project_id as a keyword argument.
        items = jama_client.get_items(project_id=project_id)
        logger.info(f"Retrieved {len(items)} items for project {project_id}.")
        # Return items, or an empty list if none found/error in client (client might return empty list on 404)
        return items if items else []
    except Exception as e:
        logger.error(f"Error in get_jama_project_items tool for project_id {project_id}: {e}", exc_info=True)
        # Return error dict for tool failures
        return {"error": f"Failed to retrieve items for Jama project {project_id}: {str(e)}"}

@mcp.tool()
async def get_jama_item_children(item_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves child items for a specific Jama item.

    Args:
        item_id: The ID (as a string) of the parent Jama item.
    """
    logger.info(f"Executing get_jama_item_children tool for parent_id: {item_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        children = jama_client.get_item_children(item_id=item_id)
        logger.info(f"Retrieved {len(children)} child items for parent {item_id}.")
        return children if children else []
    except Exception as e:
        logger.error(f"Error in get_jama_item_children tool for parent_id {item_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve children for Jama item {item_id}: {str(e)}"}

@mcp.tool()
async def get_jama_relationships(project_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves all relationships within a specific Jama project.

    Args:
        project_id: The ID (as a string) of the Jama project.
    """
    logger.info(f"Executing get_jama_relationships tool for project_id: {project_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        relationships = jama_client.get_relationships(project_id=project_id)
        logger.info(f"Retrieved {len(relationships)} relationships for project {project_id}.")
        return relationships if relationships else []
    except Exception as e:
        logger.error(f"Error in get_jama_relationships tool for project_id {project_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve relationships for Jama project {project_id}: {str(e)}"}

@mcp.tool()
async def get_jama_relationship(relationship_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific relationship by its ID.

    Args:
        relationship_id: The ID (as a string) of the relationship.
    """
    logger.info(f"Executing get_jama_relationship tool for relationship_id: {relationship_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        relationship = jama_client.get_relationship(relationship_id=relationship_id)
        if not relationship:
            return {"error": f"Relationship with ID {relationship_id} not found."}
        logger.info(f"Retrieved relationship {relationship_id}.")
        return relationship
    except Exception as e:
        logger.error(f"Error in get_jama_relationship tool for relationship_id {relationship_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve relationship {relationship_id}: {str(e)}"}

@mcp.tool()
async def get_jama_item_upstream_relationships(item_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves upstream relationships for a specific Jama item.

    Args:
        item_id: The ID (as a string) of the Jama item.
    """
    logger.info(f"Executing get_jama_item_upstream_relationships tool for item_id: {item_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        relationships = jama_client.get_items_upstream_relationships(item_id=item_id)
        logger.info(f"Retrieved {len(relationships)} upstream relationships for item {item_id}.")
        return relationships if relationships else []
    except Exception as e:
        logger.error(f"Error in get_jama_item_upstream_relationships tool for item {item_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve upstream relationships for item {item_id}: {str(e)}"}

@mcp.tool()
async def get_jama_item_downstream_relationships(item_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves downstream relationships for a specific Jama item.

    Args:
        item_id: The ID (as a string) of the Jama item.
    """
    logger.info(f"Executing get_jama_item_downstream_relationships tool for item_id: {item_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        relationships = jama_client.get_items_downstream_relationships(item_id=item_id)
        logger.info(f"Retrieved {len(relationships)} downstream relationships for item {item_id}.")
        return relationships if relationships else []
    except Exception as e:
        logger.error(f"Error in get_jama_item_downstream_relationships tool for item {item_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve downstream relationships for item {item_id}: {str(e)}"}

@mcp.tool()
async def get_jama_item_upstream_related(item_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves upstream related items for a specific Jama item.

    Args:
        item_id: The ID (as a string) of the Jama item.
    """
    logger.info(f"Executing get_jama_item_upstream_related tool for item_id: {item_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        items = jama_client.get_items_upstream_related(item_id=item_id)
        logger.info(f"Retrieved {len(items)} upstream related items for item {item_id}.")
        return items if items else []
    except Exception as e:
        logger.error(f"Error in get_jama_item_upstream_related tool for item {item_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve upstream related items for item {item_id}: {str(e)}"}

@mcp.tool()
async def get_jama_item_downstream_related(item_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves downstream related items for a specific Jama item.

    Args:
        item_id: The ID (as a string) of the Jama item.
    """
    logger.info(f"Executing get_jama_item_downstream_related tool for item_id: {item_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        items = jama_client.get_items_downstream_related(item_id=item_id)
        logger.info(f"Retrieved {len(items)} downstream related items for item {item_id}.")
        return items if items else []
    except Exception as e:
        logger.error(f"Error in get_jama_item_downstream_related tool for item {item_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve downstream related items for item {item_id}: {str(e)}"}

@mcp.tool()
async def get_jama_item_types(ctx: Context) -> list[dict]:
    """Retrieves all item types from Jama Connect."""
    logger.info("Executing get_jama_item_types tool")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        item_types = jama_client.get_item_types()
        logger.info(f"Retrieved {len(item_types)} item types.")
        return item_types if item_types else []
    except Exception as e:
        logger.error(f"Error in get_jama_item_types tool: {e}", exc_info=True)
        return {"error": f"Failed to retrieve item types: {str(e)}"}

@mcp.tool()
async def get_jama_item_type(item_type_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific item type by its ID.

    Args:
        item_type_id: The ID (as a string) of the item type.
    """
    logger.info(f"Executing get_jama_item_type tool for item_type_id: {item_type_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        item_type = jama_client.get_item_type(item_type_id=item_type_id)
        if not item_type:
             return {"error": f"Item type with ID {item_type_id} not found."}
        logger.info(f"Retrieved item type {item_type_id}.")
        return item_type
    except Exception as e:
        logger.error(f"Error in get_jama_item_type tool for item_type_id {item_type_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve item type {item_type_id}: {str(e)}"}

@mcp.tool()
async def get_jama_pick_lists(ctx: Context) -> list[dict]:
    """Retrieves all pick lists from Jama Connect."""
    logger.info("Executing get_jama_pick_lists tool")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        pick_lists = jama_client.get_pick_lists()
        logger.info(f"Retrieved {len(pick_lists)} pick lists.")
        return pick_lists if pick_lists else []
    except Exception as e:
        logger.error(f"Error in get_jama_pick_lists tool: {e}", exc_info=True)
        return {"error": f"Failed to retrieve pick lists: {str(e)}"}

@mcp.tool()
async def get_jama_pick_list(pick_list_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific pick list by its ID.

    Args:
        pick_list_id: The ID (as a string) of the pick list.
    """
    logger.info(f"Executing get_jama_pick_list tool for pick_list_id: {pick_list_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        pick_list = jama_client.get_pick_list(pick_list_id=pick_list_id)
        if not pick_list:
             return {"error": f"Pick list with ID {pick_list_id} not found."}
        logger.info(f"Retrieved pick list {pick_list_id}.")
        return pick_list
    except Exception as e:
        logger.error(f"Error in get_jama_pick_list tool for pick_list_id {pick_list_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve pick list {pick_list_id}: {str(e)}"}

@mcp.tool()
async def get_jama_pick_list_options(pick_list_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves options for a specific pick list.

    Args:
        pick_list_id: The ID (as a string) of the pick list.
    """
    logger.info(f"Executing get_jama_pick_list_options tool for pick_list_id: {pick_list_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        options = jama_client.get_pick_list_options(pick_list_id=pick_list_id)
        logger.info(f"Retrieved {len(options)} options for pick list {pick_list_id}.")
        return options if options else []
    except Exception as e:
        logger.error(f"Error in get_jama_pick_list_options tool for pick_list_id {pick_list_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve options for pick list {pick_list_id}: {str(e)}"}

@mcp.tool()
async def get_jama_pick_list_option(pick_list_option_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific pick list option by its ID.

    Args:
        pick_list_option_id: The ID (as a string) of the pick list option.
    """
    logger.info(f"Executing get_jama_pick_list_option tool for pick_list_option_id: {pick_list_option_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        option = jama_client.get_pick_list_option(pick_list_option_id=pick_list_option_id)
        if not option:
             return {"error": f"Pick list option with ID {pick_list_option_id} not found."}
        logger.info(f"Retrieved pick list option {pick_list_option_id}.")
        return option
    except Exception as e:
        logger.error(f"Error in get_jama_pick_list_option tool for pick_list_option_id {pick_list_option_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve pick list option {pick_list_option_id}: {str(e)}"}

@mcp.tool()
async def get_jama_tags(project_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves all tags for a specific project.

    Args:
        project_id: The ID (as a string) of the Jama project.
    """
    logger.info(f"Executing get_jama_tags tool for project_id: {project_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        tags = jama_client.get_tags(project=project_id) # Param name is 'project' in client
        logger.info(f"Retrieved {len(tags)} tags for project {project_id}.")
        return tags if tags else []
    except Exception as e:
        logger.error(f"Error in get_jama_tags tool for project_id {project_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve tags for project {project_id}: {str(e)}"}

@mcp.tool()
async def get_jama_tagged_items(tag_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves items associated with a specific tag.

    Args:
        tag_id: The ID (as a string) of the tag.
    """
    logger.info(f"Executing get_jama_tagged_items tool for tag_id: {tag_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        items = jama_client.get_tagged_items(tag_id=tag_id)
        logger.info(f"Retrieved {len(items)} items for tag {tag_id}.")
        return items if items else []
    except Exception as e:
        logger.error(f"Error in get_jama_tagged_items tool for tag_id {tag_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve items for tag {tag_id}: {str(e)}"}

@mcp.tool()
async def get_jama_test_cycle(test_cycle_id: str, ctx: Context) -> dict:
    """
    Retrieves details for a specific test cycle by its ID.

    Args:
        test_cycle_id: The ID (as a string) of the test cycle.
    """
    logger.info(f"Executing get_jama_test_cycle tool for test_cycle_id: {test_cycle_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        cycle = jama_client.get_test_cycle(test_cycle_id=test_cycle_id)
        if not cycle:
             return {"error": f"Test cycle with ID {test_cycle_id} not found."}
        logger.info(f"Retrieved test cycle {test_cycle_id}.")
        return cycle
    except Exception as e:
        logger.error(f"Error in get_jama_test_cycle tool for test_cycle_id {test_cycle_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve test cycle {test_cycle_id}: {str(e)}"}

@mcp.tool()
async def get_jama_test_runs(test_cycle_id: str, ctx: Context) -> list[dict]:
    """
    Retrieves test runs associated with a specific test cycle.

    Args:
        test_cycle_id: The ID (as a string) of the test cycle.
    """
    logger.info(f"Executing get_jama_test_runs tool for test_cycle_id: {test_cycle_id}")
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context["jama_client"]
        runs = jama_client.get_testruns(test_cycle_id=test_cycle_id)
        logger.info(f"Retrieved {len(runs)} test runs for cycle {test_cycle_id}.")
        return runs if runs else []
    except Exception as e:
        logger.error(f"Error in get_jama_test_runs tool for test_cycle_id {test_cycle_id}: {e}", exc_info=True)
        return {"error": f"Failed to retrieve test runs for cycle {test_cycle_id}: {str(e)}"}



@mcp.tool()
async def test_jama_connection(ctx: Context) -> dict:
    """
    Tests the connection and authentication to the Jama Connect API.
    Attempts to fetch available API endpoints as a lightweight check.
    """
    logger.info("Executing test_jama_connection tool")
    result = {"status": "unknown", "jama_client_initialized": False, "jama_api_accessible": False, "message": ""}
    try:
        jama_client: JamaClient = ctx.request_context.lifespan_context.get("jama_client")
        result["jama_client_initialized"] = jama_client is not None

        if not jama_client:
            result["status"] = "error"
            result["message"] = "JamaClient not found in context."
            return result

        # Attempt a simple API call to verify connection further
        try:
            # Using get_available_endpoints as a lightweight check
            endpoints = jama_client.get_available_endpoints()
            # Simple check if we got *something* back that looks like API response
            if isinstance(endpoints, dict) and 'data' in endpoints:
                 result["jama_api_accessible"] = True
                 result["status"] = "ok"
                 result["message"] = f"Successfully connected and fetched {len(endpoints.get('data',[]))} available endpoints."
            else:
                 result["status"] = "error"
                 result["message"] = f"Connected, but failed to fetch endpoints or response format unexpected: {endpoints}"

        except Exception as api_err:
            logger.warning(f"Test API call failed during connection test: {api_err}", exc_info=True)
            result["status"] = "error"
            result["message"] = f"JamaClient initialized, but API call failed: {str(api_err)}"
            result["jama_api_accessible"] = False

        return result

    except Exception as e:
        logger.error(f"Unexpected error in test_jama_connection tool: {e}", exc_info=True)
        result["status"] = "error"
        result["message"] = f"Unexpected error during test: {str(e)}"
        return result


if __name__ == "__main__":
    # This allows running the server directly with `python server.py`
    # However, using `mcp dev server.py` or `uv run mcp dev server.py` is recommended for development
    logger.info("Starting Jama MCP server directly (use 'mcp dev' for development features)...")
    # Note: Need to ensure environment variables are set when running this way.
    # Example check:
    # Skip credential check if in mock mode
    if not MOCK_MODE and not os.environ.get("JAMA_URL"):
        print("\nERROR: JAMA_URL environment variable is not set.")
        print("Please set JAMA_URL and authentication variables (JAMA_CLIENT_ID/SECRET or JAMA_USER/PASSWORD),")
        print("or run in mock mode by setting JAMA_MOCK_MODE=true.")
        exit(1)

    mcp.run() # This uses uvicorn defaults