# Product Requirements Document: MCP Interactive Terminal Server

## Project Overview
The goal of this project is to create an MCP (Model Context Protocol) interactive terminal server that adheres to the latest MCP standards. This server will demonstrate the use of the FastMCP package and provide tools for managing interactive terminal sessions. It will be easy to deploy and launch using the UV package manager, with seamless VS Code integration after a git checkout.

## Clarifications

### Functional Requirements

1. **MCP Server Implementation**
   - It should be built so that it can be cloned from git and immediately used with VS Code and UV without additional setup.
   - The project should use UV for dependency management and execution, making it portable and reproducible across environments.
   - The server must be implemented in Python 3.13, ensuring compatibility with the latest MCP standards as of May 2025.
   - Use the FastMCP 2.0 or later package (current version v2.2.7 as of May 2025) to build the server, leveraging its high-level Pythonic interface for MCP server creation.
   - Install FastMCP using `uv pip install fastmcp` as recommended in the official documentation.
   - FastMCP server should be created using the Pythonic decorator-based syntax for tools.
   - Use stdio transport exclusively, which is ideal for direct integration with model providers and simple testing.
   - Configure the server to run with stdio transport, making it easier to pipe input and output directly to and from the server.
   - Extend the server to support both stdio (default) and SSE transport types.
   - Allow specifying the transport type and port number via command-line arguments.
   - Default port number for SSE transport should be 8070.
   - Ensure compatibility with FastMCP's transport options.
   - Implement the server with the recommended `if __name__ == "__main__":` block pattern for maximum compatibility with all MCP clients.
   - Follow the FastMCP best practice where each server runs in its own process, allowing clients to manage multiple servers independently.

2. **VS Code Integration**
   - Create a `.vscode/mcp.json` configuration file to enable VS Code to interact with the MCP server.
   - Configure the `mcp.json` file to use UV for launching the server with stdio transport.
   - Ensure that after cloning the repository, a user only needs to have UV installed to use the server within VS Code.
   - Follow the standard MCP configuration format:
     ```json
     {
       "servers": {
         "interactive-terminal-server": {
           "type": "stdio",
           "command": "uv",
           "args": ["run", "python", "-m", "interactive.server"]
         }
       }
     }
     ```
   - Ensure the configuration works with VS Code's MCP support, allowing the tools to be used in agent mode.
   - Include documentation on how to start, stop, and interact with the server through VS Code's interface.

3. **Interactive Terminal Tools**
   - Include tools for managing interactive terminal sessions:
     - **Start Session**: A tool to start a new session by invoking a shell command (e.g., `gdb` with arguments).
     - **Wait for Prompt**: A tool to wait for one or more prompt strings or a timeout.
     - **Send Command**: A tool to send interactive commands to the session.
     - **Exit Session**: A tool to terminate the session when the shell command process finishes.
   - Implement the tools using FastMCP's decorator syntax as shown in their examples (`@mcp.tool()`).

4. **Testing**
   - Write comprehensive unit tests to validate the MCP server's functionality, correctness of tool calls, and edge cases for interactive terminal operations.
   - Utilize FastMCP's testing utilities for stdio transport to validate input and output streams.
   - Create tests that simulate model requests and verify proper responses from the server.
   - Mock stdin/stdout to test server communication specifically for stdio transport.
   - Verify proper handling of tool invocations through stdio streams, including error handling and response formatting.

### Non-Functional Requirements

1. **Ease of Deployment**
   - Utilize the UV Astral package manager to simplify deployment and launching of the server.
   - Ensure the project can be cloned and used immediately with minimal setup steps.
   - Support multiple ways to run the server as recommended in the FastMCP documentation:
     - Development mode: `uv run fastmcp dev server.py`
     - CLI mode: `uv run fastmcp run server.py:mcp_server --transport stdio`
     - Directly with Python: `uv run python -m interactive.server`
   - Configure and use stdio transport mechanism:
     - stdio: For direct integration with model providers through standard input/output streams
     - Include examples of piping input to the server and processing its output
   - Include examples of running the server with SSE transport:
     ```bash
     uv run python -m interactive.server --transport sse --port 8070
     ```
   - Ensure the server is designed to handle the stdio transport behavior where:
     - The client starts a new server process for each session
     - Communication happens through standard input/output streams
     - The server process terminates when the client disconnects
   - Document the new transport options and their configurations in the project documentation.

2. **Documentation**
   - Provide clear and concise documentation covering:
     - Steps to clone and set up the server with UV.
     - Instructions for VS Code integration after git checkout.
     - Instructions for using the interactive terminal tools.
     - Guidelines for running the tests with UV.
     - stdio transport configuration options.
     - Links to the official FastMCP GitHub repository for reference.

3. **Dependency Management**
   - Use the UV Astral package manager for managing project dependencies and virtual environments.
   - Include a pyproject.toml file for modern Python packaging and dependency specification.
   - Ensure compatibility with Linux, macOS, and Windows for cross-platform development.
   - Leverage UV's features for lockfile management, reproducible resolutions, and efficient dependency deduplication.
   - After cloning the repository, ensure that the FastMCP dependency is added to the server by running the following command:
     ```bash
     uv add --script interactive/server.py fastmcp
     ```
     This step ensures that the server is properly configured to use FastMCP.

## Development Steps

1. **Setup**
   - Initialize a Python project.
   - Install the FastMCP package using UV: `uv pip install fastmcp`

2. **Server Development**
   - Create the MCP server using FastMCP's Pythonic interface:
     ```python
     from fastmcp import FastMCP

     mcp = FastMCP("Interactive Terminal Server 🖥️")

     @mcp.tool()
     def start_session(command: str, args: list) -> str:
         """Start a new interactive session."""
         # Implementation here

     @mcp.tool()
     def wait_for_prompt(prompts: list, timeout: int) -> str:
         """Wait for one or more prompt strings or a timeout."""
         # Implementation here

     @mcp.tool()
     def send_command(command: str) -> str:
         """Send a command to the interactive session."""
         # Implementation here

     @mcp.tool()
     def exit_session() -> str:
         """Terminate the interactive session."""
         # Implementation here

     if __name__ == "__main__":
         # Run with stdio transport
         mcp.run(transport="stdio")
     ```

3. **Testing**
   - Write comprehensive unit tests to validate the MCP server's functionality, correctness of tool calls, and edge cases for interactive terminal operations.
   - Create tests that validate input and output with stdio transport:
     - Mock stdin/stdout to test server communication
     - Verify proper handling of tool invocations through stdio streams
     - Test error handling and response formatting
   - Use FastMCP's testing utilities to validate MCP compliance.
   - Test direct server execution with stdin/stdout:
     - `echo '{"type":"tool_call","name":"start_session","parameters":{"command":"gdb","args":["--args"]}}' | python interactive/server.py`
     - Verify correct JSON response to stdio

4. **Documentation**
   - Write setup and usage instructions.
   - Document the testing process.
   - Include details on stdio transport options and their configuration.
   - Include links to FastMCP documentation.
   - Provide examples of command-line usage with stdio.

5. **Deployment**
   - Configure the UV Astral package manager for deployment.
   - Test the deployment process.
   - Document different server run options with stdio transport.
   - Provide instructions for piping input/output to and from the server.

6. **UV Installation**
   - Install UV on Linux using the standalone installer:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   - Alternatively, install UV via pip:
     ```bash
     pip install uv
     ```
   - Verify the installation by running:
     ```bash
     uv --version
     ```

## Deliverables
- A Python-based MCP interactive terminal server with tools for managing interactive sessions built using FastMCP 2.0+.
- Unit tests covering all functionality.
- Documentation for setup, usage, and testing.
- Deployment configuration using UV package manager.
- Examples of stdin/stdout piping for direct interaction with the server.

## References

1. **FastMCP Documentation**
   - [FastMCP GitHub Repository](https://github.com/jlowin/fastmcp)
   - [FastMCP Server docs](https://gofastmcp.com/servers/fastmcp)
   - [FastMCP Server Tools](https://gofastmcp.com/servers/tools)
   - [FastMCP Transport Options](https://gofastmcp.com/servers/fastmcp#transport-options)

2. **UV Astral Package Manager**
   - [UV Astral Documentation](https://docs.astral.sh/uv)

3. **MCP Standard**
   - [Model Context Protocol Specification](https://modelcontextprotocol.github.io/specification/)