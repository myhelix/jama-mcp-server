# Jama MCP Tool Prompt Templates

This document provides prompt templates for the main read and write tools available in the Jama MCP server.

---

### `get_jama_item`

**Description:** Retrieves details for a specific item from Jama Connect by its ID.

**Template:**
```
<use_mcp_tool>
  <server_name>jama-mcp-uv</server_name>
  <tool_name>get_jama_item</tool_name>
  <arguments>
    {
      "item_id": "YOUR_ITEM_ID"
    }
  </arguments>
</use_mcp_tool>
```

---

### `create_item`

**Description:** Creates a new item in Jama Connect.

**Template:**
```
<use_mcp_tool>
  <server_name>jama-mcp-uv</server_name>
  <tool_name>create_item</tool_name>
  <arguments>
    {
      "project": YOUR_PROJECT_ID,
      "item_type_id": YOUR_ITEM_TYPE_ID,
      "child_item_type_id": YOUR_CHILD_ITEM_TYPE_ID,
      "location": {
        "item": YOUR_PARENT_ITEM_ID
      },
      "fields": {
        "name": "YOUR_ITEM_NAME",
        "description": "YOUR_ITEM_DESCRIPTION"
      }
    }
  </arguments>
</use_mcp_tool>
```

---

### `update_item`

**Description:** Updates an existing item in Jama Connect.

**Template:**
```
<use_mcp_tool>
  <server_name>jama-mcp-uv</server_name>
  <tool_name>update_item</tool_name>
  <arguments>
    {
      "project": YOUR_PROJECT_ID,
      "item_id": YOUR_ITEM_ID,
      "item_type_id": YOUR_ITEM_TYPE_ID,
      "child_item_type_id": YOUR_CHILD_ITEM_TYPE_ID,
      "location": {
        "item": YOUR_PARENT_ITEM_ID
      },
      "fields": {
        "name": "YOUR_UPDATED_ITEM_NAME",
        "description": "YOUR_UPDATED_ITEM_DESCRIPTION"
      }
    }
  </arguments>
</use_mcp_tool>
```

---

### `create_tag`

**Description:** Creates a new tag in a project.

**Template:**
```
<use_mcp_tool>
  <server_name>jama-mcp-uv</server_name>
  <tool_name>create_tag</tool_name>
  <arguments>
    {
      "name": "YOUR_TAG_NAME",
      "project": YOUR_PROJECT_ID
    }
  </arguments>
</use_mcp_tool>
```

---

### `add_jama_item_tag`

**Description:** Adds an existing tag to an item.

**Template:**
```
<use_mcp_tool>
  <server_name>jama-mcp-uv</server_name>
  <tool_name>add_jama_item_tag</tool_name>
  <arguments>
    {
      "item_id": YOUR_ITEM_ID,
      "tag_id": YOUR_TAG_ID
    }
  </arguments>
</use_mcp_tool>