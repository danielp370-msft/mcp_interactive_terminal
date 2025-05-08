# MCP Interactive Terminal Server

## Overview
The MCP Interactive Terminal Server is a Python-based server built using the FastMCP package. It provides tools for managing interactive terminal sessions and adheres to the latest MCP standards. The server supports both stdio (default) and SSE transport mechanisms, making it versatile for various use cases.

## Installation

### Prerequisites
1. **Python 3.13 or later**
   Ensure you have Python 3.13 installed on your system.

2. **UV Astral Package Manager**
   Install UV using one of the following methods:
   - **Standalone Installer**:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   - **Pip Installation**:
     ```bash
     pip install uv
     ```
   Verify the installation:
   ```bash
   uv --version
   ```

### Clone the Repository
Clone the repository to your local machine:
```bash
git clone <repository-url>
cd mcp_interactive_terminal
```

## Usage

### Running the Server

#### Using VS Code
1. Open the project in VS Code.
2. Ensure the `.vscode/mcp.json` file is configured correctly:
   ```json
   {
     "servers": {
       "interactive-terminal-server": {
         "type": "stdio",
         "command": "uv",
         "args": ["run", "${workspaceFolder}/interactive/server.py"]
       }
     }
   }
   ```
3. Start the server using the MCP interface in VS Code.

#### Using the Command Line
- **Stdio Transport (Default)**:
  ```bash
  uv run python -m interactive.server
  ```
- **SSE Transport**:
  ```bash
  uv run python -m interactive.server --transport sse --port 8070
  ```

### Interactive Terminal Tools
The server provides the following tools:

1. **Start Session**:
   - **Description**: Start a new interactive session by invoking a shell command.
   - **Parameters**:
     - `command` (str): The command to start the session (e.g., `python`).
     - `args` (list): Arguments for the command.
     - `log_file` (str, optional): Path to a log file where session output will be written. If not provided, no logging will occur.
   - **Returns**: A message with the session ID.

2. **Wait for Output or Prompt**:
   - **Description**: Wait for specific output, a prompt, or gather output within a timeout.
   - **Parameters**:
     - `session_id` (int): The ID of the session to monitor.
     - `prompts` (list): A list of strings to detect in the output (e.g., prompts or specific text).
     - `timeout` (int): The maximum time to wait for the output, in seconds.
   - **Returns**: A message indicating the detected output, or a timeout message if no match is found.
   - **Note**: This function can also be used to retrieve the current output buffer.

3. **Send Command**:
   - **Description**: Send a command to the interactive session.
   - **Parameters**:
     - `session_id` (int): The session ID.
     - `command` (str): The command to send.
   - **Returns**: A message indicating success or failure.

4. **Exit Session**:
   - **Description**: Terminate the interactive session.
   - **Parameters**:
     - `session_id` (int): The ID of the session to terminate.
   - **Returns**: A message indicating the session termination status.

5. **Get Active Sessions**:
   - **Description**: Retrieve a list of all active interactive sessions.
   - **Returns**: A dictionary containing session IDs and their statuses.

### Starting a Session

You can start a new session using the `start_session` tool. 

```python
start_session(command: str, args: list, log_file: str = None)
```

- `command`: The command to start the interactive session (e.g., 'python').
- `args`: A list of arguments to pass to the command.
- `log_file`: Optional log file to write session output.

Example:

```python
start_session("python", ["-i"])
```

This will start a Python interactive session.

### Testing
Run the unit tests to validate the server's functionality:
```bash
uv run python3 -m unittest
```

## References
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [UV Astral Documentation](https://docs.astral.sh/uv)
- [Model Context Protocol Specification](https://modelcontextprotocol.github.io/specification/)