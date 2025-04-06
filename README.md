# Jama Connect MCP Server (Unofficial)

This project provides a Model Context Protocol (MCP) server that exposes read-only tools for interacting with a Jama Connect instance. It acts as an MCP wrapper around the official [Jama Software `py-jama-rest-client`](https://github.com/JamaSoftware/py-jama-rest-client) library.

**Disclaimer:** This is a third-party, open-source project and is not officially affiliated with or endorsed by Jama Software.

**Note:** This server currently only supports read-only operations. Write operations may be added in future updates.

## Philosophy: Local Execution & Security

This MCP server is **intentionally not published** as a package on PyPI or other indices. This decision encourages users to:

1.  **Clone/Fork the Repository:** Obtain the code directly.
2.  **Inspect the Code:** Understand exactly what the server does before running it, especially concerning API interactions and credential handling.
3.  **Adapt as Needed:** Modify the code for specific enterprise requirements or security postures.

This approach prioritizes security awareness and user control over convenience, mitigating risks associated with installing potentially unverified third-party packages. Local execution by cloning the repository is the only supported method at this time.

## Prerequisites

*   **Python:** Version 3.12 or higher.
*   **uv:** The Python package installer and virtual environment manager. ([Installation Guide](https://github.com/astral-sh/uv#installation))
*   **Git:** For cloning the repository.

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/t-j-thomas/jama-mcp-server.git
    cd jama-mcp-server
    ```

2.  **Install Dependencies:**
    Navigate into the server directory and use `uv` to create a virtual environment and install dependencies.
    ```bash
    uv sync
    ```
    This installs required dependencies, including `boto3` if you plan to use AWS Parameter Store for credentials.

## Configuration

The server requires environment variables to connect to your Jama Connect instance using **OAuth 2.0**. Credentials can be provided directly or fetched securely from AWS Parameter Store.

**Authentication Methods (Priority Order):**

1.  **AWS Parameter Store (Recommended for Security):**
    *   `JAMA_URL` (Required): The base URL of your Jama Connect instance (e.g., `https://yourcompany.jamacloud.com`).
    *   `JAMA_AWS_SECRET_PATH` (Required for this method): The full name/path of the secret in AWS Parameter Store containing your Jama credentials.
        *   The secret value **must** be a JSON string with the following structure: `{"client_id": "YOUR_JAMA_CLIENT_ID", "client_secret": "YOUR_JAMA_CLIENT_SECRET"}`.
    *   `JAMA_AWS_PROFILE` (Optional): The AWS named profile to use for authenticating to AWS. If not set, `boto3` will use its default credential resolution (e.g., environment variables, EC2 instance profile).
    *   **Note:** Using this method requires the `boto3` library to be installed (`uv sync` handles this) and appropriate AWS permissions for the server's execution environment to access the specified Parameter Store secret.

2.  **Direct Environment Variables (Fallback):**
    *   `JAMA_URL` (Required): The base URL of your Jama Connect instance.
    *   `JAMA_CLIENT_ID` (Required if not using AWS): Your Jama API OAuth Client ID.
    *   `JAMA_CLIENT_SECRET` (Required if not using AWS): Your Jama API OAuth Client Secret.

If `JAMA_AWS_SECRET_PATH` is set, it takes precedence. If it's not set, the server looks for `JAMA_CLIENT_ID` and `JAMA_CLIENT_SECRET`. If neither method provides the necessary credentials (and Mock Mode is off), the server will fail to start.

**Mock Mode (Optional):**

For testing without connecting to a live Jama instance:

*   `JAMA_MOCK_MODE`: Set to `true` to use the built-in mock client. The server will return predefined sample data. Any other value (or omitting the variable) disables mock mode.

**Setting Environment Variables:**

Set these variables in the environment where the MCP client will launch the server process. This could be:
*   Your terminal session (`export JAMA_URL=...`).
*   Directly within the MCP client's server configuration (see below).

## Running the Server (Standalone)

You can run the server directly for basic checks using `uv` (ensure environment variables are set):

```bash
# Ensure you are in the jama-mcp-server directory
uv run python jama_mcp/server.py
```
## Testing with `test_mcp_client.py`

This repository includes a test client script (`test_mcp_client.py`) that can be used to directly invoke the server's tools via stdio, primarily for debugging or quick checks, especially in mock mode.

To run the test client:

```bash
# Ensure you are in the jama-mcp-server directory
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
    "jama-mcp": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "jama_mcp/server.py"
      ],
      
      "cwd": "/path/to/your/clone/jama-mcp-server",
      "env": {
        "JAMA_URL": "https://your.jama.instance.com",
        "JAMA_CLIENT_ID": "your_client_id",
        "JAMA_CLIENT_SECRET": "your_client_secret",
        "JAMA_AWS_SECRET_PATH": "/path/to/your/jama/secret",
        "JAMA_MOCK_MODE": "false"
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

*   **Connection/Authentication Errors:**
    *   Verify `JAMA_URL` is correct.
    *   If using direct env vars: Check `JAMA_CLIENT_ID`, `JAMA_CLIENT_SECRET`.
    *   If using AWS Parameter Store:
        *   Verify `JAMA_AWS_SECRET_PATH` is correct.
        *   Ensure the server's execution environment has permissions to read the secret (check IAM roles/policies).
        *   Verify the secret value is valid JSON: `{"client_id": "...", "client_secret": "..."}`.
        *   Check if `boto3` is installed correctly (`uv sync`).
        *   If using `JAMA_AWS_PROFILE`, ensure the profile exists and is configured correctly.
    *   Check Jama API client permissions in Jama Connect itself.
*   **Tool Errors:** Check arguments passed to the tool. Consult server logs (stderr) for more details.
*   **Mock Mode Not Working:** Ensure `JAMA_MOCK_MODE` environment variable is set to exactly `true`.