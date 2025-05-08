# MCP Interactive Terminal Server

## Overview
The MCP Interactive Terminal Server allows an agent to interact with a command-line driven prompt. This is useful for automating and managing interactive terminal commands such as gdb, a UART console, or any other REPL-based tool. Built using the FastMCP package, it provides tools for managing interactive terminal sessions and adheres to the latest MCP standards. The server supports three transport options offered by FastMCP: stdio (default), sse, and streamable-http, making it versatile for various use cases.

## Installation

### Prerequisites
1. **Python 3.12 or later**
   Ensure you have Python 3.12 or newer installed on your system.

2. **UV Astral Package Manager**
   UV Astral is an optional package manager that handles dependencies. If you use it, it will provide Python with only the dependencies you need. If you invoke commands that require other dependencies, you can add them to the UV dependencies so that they get loaded as well. It may be better to do this in the downstream package or not use UV if the environment is set up to provide all packages directly.

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

### Adding Dependencies to UV Astral

If you are using UV Astral as your package manager, you can optionally add Python and other dependencies to its configuration. For detailed instructions on managing dependencies with UV Astral, refer to the [UV Astral official documentation](https://docs.astral.sh/uv/guides/projects/).

### Clone the Repository
Clone the repository to your local machine:
```bash
git clone https://github.com/danielp370-msft/mcp_interactive_terminal
cd mcp_interactive_terminal
```

## Usage

### Running the Server

#### Using VS Code
1. Open the project in VS Code.
2. Ensure the `.vscode/mcp.json` file is configured correctly. You can use either of the following examples:

   **Example 1: Using uv (package manager)**
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

   **Example 2: Using python directly (current default)**
   ```json
   {
     "servers": {
       "interactive-terminal-server": {
         "type": "stdio",
         "command": "python3.13",
         "args": ["${workspaceFolder}/interactive/server.py"]
       }
     }
   }
   ```

   **Example 3: Using streamable-http transport**
   ```json
   {
     "servers": {
       "interactive-terminal-server": {
         "type": "http",
         "url": "http://localhost:8070/mcp/"
       }
     }
   }
   ```
3. Start the server using the MCP interface in VS Code.

#### Using the Command Line
> **Note:** You only need to invoke the server on the command line if you are using non-stdio transport options (like `streamable-http`) or if you want to run it outside of VS Code. For stdio, the VS Code MCP interface can launch the server automatically.

- **Stdio Transport (Default)**:
  ```bash
  uv run python -m interactive.server
  ```
  
  You can also run the server without `uv` if you want to use the packages provided by your runtime environment:
  ```bash
  python -m interactive.server
  ```
- **Streamable HTTP Transport**:
  ```bash
  uv run python -m interactive.server --transport streamable-http --port 8070
  ```
  
  Or without `uv`:
  ```bash
  python -m interactive.server --transport streamable-http --port 8070
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
- [UV Astral Project Documentation](https://docs.astral.sh/uv/guides/projects/)
- [Model Context Protocol Specification](https://modelcontextprotocol.github.io/specification/)

## Acknowledgments

This product was vibe coded with the help of Daniel Potts, who deserves special thanks for pestering the AI to do endless rounds of interactive testing — truly a champion of quality assurance (and patience). No human directly wrote any code, documentation, or even bothered to help push into a PR for this project. All code and documentation were generated with the assistance of GitHub Copilot (OpenAI GPT-4).