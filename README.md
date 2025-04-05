# Jama Connect MCP Server (Third-Party)

This project provides a Model Context Protocol (MCP) server that exposes read-only tools for interacting with a Jama Connect instance. It acts as a wrapper around the official [Jama Software `py-jama-rest-client`](https://github.com/JamaSoftware/py-jama-rest-client) library.

**Disclaimer:** This is a third-party, open-source project and is not officially affiliated with or endorsed by Jama Software.

**Note:** This server currently only supports read-only operations. Write operations may be added in future updates.

## Philosophy: Local Execution & Security

This MCP server is **intentionally not published** as a package on PyPI or other indices. This decision encourages users to:

1.  **Clone the Repository:** Obtain the code directly.
2.  **Inspect the Code:** Understand exactly what the server does before running it, especially concerning API interactions and credential handling.
3.  **Adapt as Needed:** Modify the code for specific enterprise requirements or security postures.

This approach prioritizes security awareness and user control over convenience, mitigating risks associated with installing potentially unverified third-party packages. Local execution by cloning the repository is the only supported method at this time.

## Prerequisites

*   **Python:** Version 3.9 or higher recommended.
*   **uv:** The Python package installer and virtual environment manager. ([Installation Guide](https://github.com/astral-sh/uv#installation))
*   **Git:** For cloning the repository.

## Setup

1.  **Clone the Repository:**
    ```bash
    # Replace <repository_url> with the actual URL
    git clone <repository_url> jama-mcp
    cd jama-mcp
    ```

2.  **Install Dependencies:**
    Navigate into the server directory and use `uv` to create a virtual environment and install dependencies.
    ```bash
    cd jama_mcp_server
    uv sync
    ```

## Configuration

The server requires environment variables to connect to your Jama Connect instance using **OAuth 2.0 only**.

**Required Environment Variables:**

*   `JAMA_URL`: The base URL of your Jama Connect instance (e.g., `https://yourcompany.jamacloud.com`).
*   `JAMA_CLIENT_ID`: Your Jama API OAuth Client ID.
*   `JAMA_CLIENT_SECRET`: Your Jama API OAuth Client Secret.

If these variables are not correctly set, the server will fail to start (unless Mock Mode is enabled).

**Mock Mode (Optional):**

For testing without connecting to a live Jama instance:

*   `JAMA_MOCK_MODE`: Set to `true` to use the built-in mock client. The server will return predefined sample data. Any other value (or omitting the variable) disables mock mode.

**Setting Environment Variables:**

Set these variables in the environment where the MCP client will launch the server process. This could be:
*   Your terminal session (`export JAMA_URL=...`).
*   A `.env` file loaded by your launch mechanism (requires additional tooling).
*   Directly within the MCP client's server configuration (see below).

## Running the Server (Standalone)

You can run the server directly for basic checks using `uv` (ensure environment variables are set):

```bash
# Ensure you are in the jama_mcp_server directory
uv run python server.py
```
## Testing with `test_mcp_client.py`

This repository includes a test client script (`test_mcp_client.py`) that can be used to directly invoke the server's tools via stdio, primarily for debugging or quick checks, especially in mock mode.

To run the test client:

```bash
# Ensure you are in the jama_mcp_server directory
# This script automatically sets JAMA_MOCK_MODE=true for the server it launches
uv run python test_mcp_client.py
```

The script will start the server, call various predefined tools (including success and expected failure cases in mock mode), print the results, and provide a summary. You can modify this script to test specific tools or scenarios.


## Integration with MCP Clients (Local Execution)

Configure your MCP client (like Cline, RooCode, Claude Desktop) to launch this server via its settings (e.g., `mcp_settings.json`).

**Example Configuration (`mcp_settings.json`):**

```json
{
  "mcpServers": {
    // ... other servers ...

    "jama-mcp": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "server.py"
      ],
      // "cwd" MUST point to the 'jama_mcp_server' directory
      // within your cloned 'jama-mcp' repository.
      // Adjust relative path based on where client runs from.
      // Use the absolute path to the server directory
      "cwd": "/home/.../jama_mcp_server",
      "env": {
        // Option 1: Pass credentials via client config
        // "JAMA_URL": "https://your.jama.instance.com",
        // "JAMA_CLIENT_ID": "your_client_id",
        // "JAMA_CLIENT_SECRET": "your_client_secret",

        // Option 2: Use Mock Mode via client config
        "JAMA_MOCK_MODE": "true"

        // Note: If not using Mock Mode and not passing credentials
        // here, ensure the required JAMA_URL, JAMA_CLIENT_ID, and
        // JAMA_CLIENT_SECRET variables are set in the environment
        // where the client launches the server process.
      }
    }
  }
}
```

**Key Points:**
*   The `cwd` path is critical for `uv` to find the project context.
*   Ensure the required Jama environment variables are available to the server process.

## Available Tools

This server provides various read-only tools. See your MCP client interface for the full list after connecting. Examples include `get_jama_projects`, `get_jama_item`, `get_jama_relationships`, etc.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions and feedback are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines.

## Troubleshooting

*   **Connection/Authentication Errors:** Verify `JAMA_URL`, `JAMA_CLIENT_ID`, `JAMA_CLIENT_SECRET` are correctly set in the server's execution environment. Check Jama permissions.
*   **Tool Errors:** Check arguments. Consult server logs (stderr).
*   **Mock Mode Not Working:** Ensure `JAMA_MOCK_MODE` is exactly `true`.