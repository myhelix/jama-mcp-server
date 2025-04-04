import logging

logger = logging.getLogger(__name__)

class MockJamaClient:
    """
    A mock implementation of the JamaClient for testing the MCP server
    without connecting to a real Jama instance.
    """
    def get_projects(self):
        logger.info("MOCK: get_projects() called")
        return [{"id": 1, "name": "Mock Project Alpha", "projectKey": "MPA"},
                {"id": 2, "name": "Mock Project Beta", "projectKey": "MPB"}]

    def get_item(self, item_id: str): # Changed type hint to str
        logger.info(f"MOCK: get_item(item_id='{item_id}') called")
        # Compare as strings or convert if necessary for logic
        if item_id == "123":
            return {"id": 123, "documentKey": "MOCK-1", "fields": {"name": "Mock Item 123", "description": "A sample item."}}
        elif item_id == "456":
             return {"id": 456, "documentKey": "MOCK-2", "fields": {"name": "Another Mock Item", "description": "Details here."}}
        else:
            # Simulate not found for other IDs in mock mode
            logger.warning(f"MOCK: Item ID {item_id} not found.")
            return None # Or raise an appropriate exception if the real client does

    def get_available_endpoints(self):
         logger.info("MOCK: get_available_endpoints() called")
         # Return a structure similar to the real API if known, otherwise simple dict
         return {"data": [{"path": "/mock", "method": "GET"}]}

    # Note: The real client's get_items takes project_id as a keyword argument
    # Note: The real client's get_items takes project_id as a keyword argument
    def get_items(self, project_id: str = None): # Changed type hint to str, kept default None
        if project_id is not None:
            logger.info(f"MOCK: get_items(project_id='{project_id}') called")
            # Compare as strings or convert if necessary for logic
            if project_id == "1": # Mock Project Alpha
                # Use self.get_item with string ID
                item = self.get_item("123")
                return [item] if item else []
            elif project_id == "2": # Mock Project Beta
                 item = self.get_item("456")
                 return [item] if item else []
            else:
                logger.warning(f"MOCK: Project ID {project_id} not found for get_items.")
                return [] # No items for other mock projects
        else:
             # Mock behavior if get_items is called without project_id (if applicable)
             logger.warning("MOCK: get_items() called without project_id, returning empty list.")
             return []

    # Add mock methods for other functions as needed, e.g.:
    # def get_item_children(self, item_id: int):
    #     logger.info(f"MOCK: get_item_children({item_id}) called")
    #     if item_id == 123:
    #         return [{"id": 789, "documentKey": "MOCK-3", "fields": {"name": "Child Item 1", "description": "..."}},
    #                 {"id": 790, "documentKey": "MOCK-4", "fields": {"name": "Child Item 2", "description": "..."}}]
    #     else:
    #         logger.warning(f"MOCK: Parent item ID {item_id} not found for get_item_children.")
    #         return []