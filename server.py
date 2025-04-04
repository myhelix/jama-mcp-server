import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

from mcp.server.fastmcp import FastMCP, Context
# Check if we need the real client or can use a mock
MOCK_MODE = os.environ.get("JAMA_MOCK_MODE", "false").lower() == "true"

if not MOCK_MODE:
    from py_jama_rest_client.client import JamaClient
else:
    # Define a mock client if in mock mode
    class MockJamaClient:
        def get_projects(self):
            logger.info("MOCK: get_projects() called")
            return [{"id": 1, "name": "Mock Project Alpha", "projectKey": "MPA"},
                    {"id": 2, "name": "Mock Project Beta", "projectKey": "MPB"}]

        def get_item(self, item_id: int):
            logger.info(f"MOCK: get_item({item_id}) called")
            if item_id == 123:
                return {"id": 123, "documentKey": "MOCK-1", "fields": {"name": "Mock Item 123", "description": "A sample item."}}
            elif item_id == 456:
                 return {"id": 456, "documentKey": "MOCK-2", "fields": {"name": "Another Mock Item", "description": "Details here."}}
            else:
                # Simulate not found for other IDs in mock mode
                return None # Or raise an appropriate exception if the real client does

        def get_available_endpoints(self):
             logger.info("MOCK: get_available_endpoints() called")
             # Return a structure similar to the real API if known, otherwise simple dict
             return {"data": [{"path": "/mock", "method": "GET"}]}

    JamaClient = MockJamaClient # Use the mock class instead of the real one

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
async def get_jama_item(item_id: int, ctx: Context) -> dict:
    """
    Retrieves details for a specific item from Jama Connect by its ID.

    Args:
        item_id: The ID of the Jama item to retrieve.
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