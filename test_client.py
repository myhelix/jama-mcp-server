import asyncio
import os
import sys
import logging

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Configure basic logging for the client
logging.basicConfig(level=logging.INFO, format='%(asctime)s - CLIENT - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """
    Connects to the Jama MCP server via stdio and tests its tools.
    """
    # Ensure the server runs in the correct uv environment and in mock mode
    # We use 'uv run python server.py' to ensure the server runs within its venv
    server_command = ["uv", "run", "python", "server.py"]
    server_env = {"JAMA_MOCK_MODE": "true"} # Ensure server starts in mock mode

    logger.info(f"Starting server with command: {' '.join(server_command)}")
    logger.info(f"Server environment: {server_env}")

    server_params = StdioServerParameters(
        command=server_command[0], # The executable ('uv')
        args=server_command[1:],   # The arguments ('run', 'python', 'server.py')
        env=server_env,
        cwd=os.path.dirname(__file__) # Run server from the script's directory
    )

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            logger.info("stdio_client connected, establishing ClientSession...")
            async with ClientSession(read_stream, write_stream) as session:
                logger.info("Initializing MCP session...")
                try:
                    init_result = await session.initialize()
                    logger.info(f"MCP Session Initialized. Server capabilities: {init_result.capabilities}")
                except Exception as init_err:
                    logger.error(f"MCP Initialization failed: {init_err}", exc_info=True)
                    return # Cannot proceed without initialization

                # --- Test Tool Calls ---
                test_results = {}

                # 1. Test Connection Tool
                logger.info("Calling tool: test_jama_connection")
                try:
                    result = await session.call_tool("test_jama_connection")
                    logger.info(f"Result (test_jama_connection): {result}")
                    test_results["test_connection"] = result
                except Exception as e:
                    logger.error(f"Error calling test_jama_connection: {e}", exc_info=True)
                    test_results["test_connection"] = {"error": str(e)}

                # 2. Get Projects Tool
                logger.info("Calling tool: get_jama_projects")
                try:
                    result = await session.call_tool("get_jama_projects")
                    logger.info(f"Result (get_jama_projects): {result}")
                    test_results["get_projects"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_projects: {e}", exc_info=True)
                    test_results["get_projects"] = {"error": str(e)}

                # 3. Get Item Tool (Existing Mock ID)
                logger.info("Calling tool: get_jama_item (item_id=123)")
                try:
                    result = await session.call_tool("get_jama_item", arguments={"item_id": "123"}) # Pass ID as string
                    logger.info(f"Result (get_jama_item, id=123): {result}")
                    test_results["get_item_123"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_item(123): {e}", exc_info=True)
                    test_results["get_item_123"] = {"error": str(e)}

                # 4. Get Item Tool (Non-Existing Mock ID)
                logger.info("Calling tool: get_jama_item (item_id=999)")
                try:
                    result = await session.call_tool("get_jama_item", arguments={"item_id": "999"}) # Pass ID as string
                    logger.info(f"Result (get_jama_item, id=999): {result}")
                    test_results["get_item_999"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_item(999): {e}", exc_info=True)
                    test_results["get_item_999"] = {"error": str(e)}

                # 5. Get Project Items Tool (Existing Mock Project ID 1)
                logger.info("Calling tool: get_jama_project_items (project_id=1)")
                try:
                    result = await session.call_tool("get_jama_project_items", arguments={"project_id": "1"}) # Pass ID as string
                    logger.info(f"Result (get_jama_project_items, project_id=1): {result}")
                    test_results["get_project_items_1"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_project_items(1): {e}", exc_info=True)
                    test_results["get_project_items_1"] = {"error": str(e)}

                # 6. Get Project Items Tool (Non-Existing Mock Project ID 99)
                logger.info("Calling tool: get_jama_project_items (project_id=99)")
                try:
                    result = await session.call_tool("get_jama_project_items", arguments={"project_id": "99"}) # Pass ID as string
                    logger.info(f"Result (get_jama_project_items, project_id=99): {result}")
                    test_results["get_project_items_99"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_project_items(99): {e}", exc_info=True)
                    test_results["get_project_items_99"] = {"error": str(e)}

                # 7. Get Item Children (Parent ID 123)
                logger.info("Calling tool: get_jama_item_children (item_id=123)")
                try:
                    result = await session.call_tool("get_jama_item_children", arguments={"item_id": "123"})
                    logger.info(f"Result (get_jama_item_children, id=123): {result}")
                    test_results["get_item_children_123"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_item_children(123): {e}", exc_info=True)
                    test_results["get_item_children_123"] = {"error": str(e)}

                # 8. Get Item Children (Parent ID 999)
                logger.info("Calling tool: get_jama_item_children (item_id=999)")
                try:
                    result = await session.call_tool("get_jama_item_children", arguments={"item_id": "999"})
                    logger.info(f"Result (get_jama_item_children, id=999): {result}")
                    test_results["get_item_children_999"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_item_children(999): {e}", exc_info=True)
                    test_results["get_item_children_999"] = {"error": str(e)}

                # 9. Get Relationships (Project ID 1)
                logger.info("Calling tool: get_jama_relationships (project_id=1)")
                try:
                    result = await session.call_tool("get_jama_relationships", arguments={"project_id": "1"})
                    logger.info(f"Result (get_jama_relationships, project_id=1): {result}")
                    test_results["get_relationships_1"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_relationships(1): {e}", exc_info=True)
                    test_results["get_relationships_1"] = {"error": str(e)}

                # 10. Get Relationship (ID 101)
                logger.info("Calling tool: get_jama_relationship (relationship_id=101)")
                try:
                    result = await session.call_tool("get_jama_relationship", arguments={"relationship_id": "101"})
                    logger.info(f"Result (get_jama_relationship, id=101): {result}")
                    test_results["get_relationship_101"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_relationship(101): {e}", exc_info=True)
                    test_results["get_relationship_101"] = {"error": str(e)}

                # Add more tests for other tools as needed...
                # e.g., get_jama_item_upstream_relationships, get_jama_item_types, etc.
                # Remember to use appropriate mock IDs defined in mock_client.py

                # Example: Get Item Types
                logger.info("Calling tool: get_jama_item_types")
                try:
                    result = await session.call_tool("get_jama_item_types")
                    logger.info(f"Result (get_jama_item_types): {result}")
                    test_results["get_item_types"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_item_types: {e}", exc_info=True)
                    test_results["get_item_types"] = {"error": str(e)}

                # Example: Get Tags for Project 1
                logger.info("Calling tool: get_jama_tags (project_id=1)")
                try:
                    result = await session.call_tool("get_jama_tags", arguments={"project_id": "1"})
                    logger.info(f"Result (get_jama_tags, project_id=1): {result}")
                    test_results["get_tags_1"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_tags(1): {e}", exc_info=True)
                    test_results["get_tags_1"] = {"error": str(e)}

                # Example: Get Test Runs for Cycle 501
                logger.info("Calling tool: get_jama_test_runs (test_cycle_id=501)")
                try:
                    result = await session.call_tool("get_jama_test_runs", arguments={"test_cycle_id": "501"})
                    logger.info(f"Result (get_jama_test_runs, cycle=501): {result}")
                    test_results["get_test_runs_501"] = result
                except Exception as e:
                    logger.error(f"Error calling get_jama_test_runs(501): {e}", exc_info=True)
                    test_results["get_test_runs_501"] = {"error": str(e)}


                # --- Print Summary ---
                print("\n--- Test Summary ---")
                for test_name, result_data in test_results.items():
                    status = "PASS" if "error" not in result_data else "FAIL"
                    print(f"{test_name}: {status} - {result_data}")
                print("--------------------\n")

            logger.info("ClientSession closed.")
        logger.info("stdio_client disconnected.")

    except Exception as e:
        logger.error(f"An error occurred during the test client execution: {e}", exc_info=True)

if __name__ == "__main__":
    # Ensure the script is run from the project root or adjust paths accordingly
    # For simplicity, assuming it's run from within jama_mcp_server directory
    # or that server.py path is correct relative to cwd.
    asyncio.run(main())