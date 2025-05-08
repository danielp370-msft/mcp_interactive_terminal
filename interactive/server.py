# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp",
# ]
# ///
from fastmcp import FastMCP
import argparse
import subprocess
import time
import threading
import pty
import os
import atexit
import signal
import datetime

# Add a debug macro-like function
DEBUG_MODE = True

def debug_log(message):
    if DEBUG_MODE:
        print(message, flush=True)

mcp = FastMCP("Interactive Terminal Server 🖥️")

# Parse command-line arguments
DEFAULT_PORT = 8070
parser = argparse.ArgumentParser(description="Run the Interactive Terminal Server 🖥️")
parser.add_argument("--transport", type=str, default="stdio", choices=["stdio", "sse"], help="Transport type (default: stdio)")
parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port number for SSE transport (default: {DEFAULT_PORT})")
args = parser.parse_args()

sessions = {}
session_buffers = {}
session_seek_positions = {}

# Ensure all subprocesses are terminated on program exit
def cleanup_sessions():
    for session_id, (process, master_fd) in list(sessions.items()):
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            debug_log(f"DEBUG: Cleanup - Terminated session {session_id}.")
        except Exception as e:
            debug_log(f"DEBUG: Cleanup - Failed to terminate session {session_id}: {e}")
        finally:
            os.close(master_fd)
            debug_log(f"DEBUG: Cleanup - Closed master_fd for session {session_id}.")

atexit.register(cleanup_sessions)

# Updated capture_output function to remove verbose handling
def capture_output(session_id, master_fd, log_file=None):
    buffer = session_buffers[session_id] = []
    while True:
        try:
            output = os.read(master_fd, 1024).decode()
            buffer.append(output)
            debug_log(f"DEBUG: Captured output: {output}")
            if log_file:
                with open(log_file, "a") as f:
                    f.write(output)
        except OSError:
            break

# Updated start_session function to remove verbose parameter
@mcp.tool()
def start_session(command: str, args: list, log_file: str = None) -> str:
    """Start a new interactive session for a program.

    Parameters:
        command (str): The command to start the interactive session (e.g., 'python').
        args (list): A list of arguments to pass to the command.
        log_file (str): Optional log file to write session output.

    Returns:
        str: A message indicating the session ID if successful, or an error message if the session could not be started.
    """
    session_id = len(sessions) + 1
    try:
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(
            [command] + args,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            text=True,
            bufsize=1,
            universal_newlines=True,
            start_new_session=True  # Isolate the process to prevent signal propagation
        )
    except FileNotFoundError:
        return f"Error: Command '{command}' not found."
    except Exception as e:
        return f"Error: Failed to start command '{command}'. Details: {e}"

    sessions[session_id] = (process, master_fd)

    # Start a thread to capture the process output
    threading.Thread(target=capture_output, args=(session_id, master_fd, log_file), daemon=True).start()

    return f"Session {session_id} started."

@mcp.tool()
def wait_for_output_or_prompt(session_id: int, prompts: list, timeout: int, return_output: bool = False) -> str:
    """Wait for specific output, a prompt, or gather output within a timeout.

    Parameters:
        session_id (int): The ID of the session to monitor.
        prompts (list): A list of strings to detect in the output (e.g., prompts or specific text).
        timeout (int): The maximum time to wait for the output, in seconds.
        return_output (bool): Whether to return the captured output until timeout or prompt is reached.

    Returns:
        str: A message indicating the detected output, or a timeout message if no match is found. If return_output is True, includes the captured output.
    """
    if session_id not in session_buffers:
        debug_log("DEBUG: Invalid session ID.")
        return "Invalid session ID."

    buffer = session_buffers[session_id]
    start_time = time.time()

    # Initialize seek position for the session if not already set
    if session_id not in session_seek_positions:
        session_seek_positions[session_id] = 0

    seek_position = session_seek_positions[session_id]
    debug_log(f"DEBUG: Initial seek position for session {session_id}: {seek_position}")

    while time.time() - start_time < timeout:
        # Process all data from the buffer
        new_data = "".join(buffer)
        debug_log(f"DEBUG: Full buffer data for session {session_id}: {new_data}")

        for prompt in prompts:
            prompt_index = new_data.find(prompt, seek_position)
            if prompt_index != -1:
                end_position = prompt_index + len(prompt)
                session_seek_positions[session_id] = end_position  # Save seek position
                debug_log(f"DEBUG: Prompt '{prompt}' detected for session {session_id} at position {prompt_index}. Updated seek position: {end_position}")
                if return_output:
                    captured_output = new_data[:end_position]
                    debug_log(f"DEBUG: Captured output for session {session_id}: {captured_output}")
                    return f"Output '{prompt}' detected. Captured output: {captured_output}"
                return f"Output '{prompt}' detected."

        # Update seek position to the end of the buffer
        session_seek_positions[session_id] = len(new_data)
        debug_log(f"DEBUG: Updated seek position for session {session_id}: {session_seek_positions[session_id]}")
        time.sleep(0.1)

    session_seek_positions[session_id] = len(new_data)  # Save seek position on timeout
    debug_log(f"DEBUG: Timeout reached for session {session_id}. Final seek position: {session_seek_positions[session_id]}")
    if return_output:
        captured_output = new_data
        debug_log(f"DEBUG: Captured output on timeout for session {session_id}: {captured_output}")
        return f"Timeout reached without detecting any specified output. Captured output: {captured_output}"
    return "Timeout reached without detecting any specified output."

@mcp.tool()
def send_command(session_id: int, command: str) -> str:
    """Send a command to the interactive session.

    Parameters:
        session_id (int): The ID of the session to send the command to.
        command (str): The command to send to the session. Include a newline in str if that's normally expected to invoke the command.

    Returns:
        str: A message indicating success or failure of sending the command.
    """
    session_data = sessions.get(session_id)
    if not session_data:
        return "Invalid session ID."

    process, master_fd = session_data

    try:
        os.write(master_fd, (command + "\n").encode())
        return "Command sent successfully."
    except OSError as e:
        return f"Failed to send command: {e}"

@mcp.tool()
def exit_session(session_id: int) -> str:
    """Terminate the interactive session.

    Parameters:
        session_id (int): The ID of the session to terminate.

    Returns:
        str: A message indicating the session termination status or an error message if termination failed.
    """
    session_data = sessions.pop(session_id, None)
    if not session_data:
        return "Invalid session ID."

    process, master_fd = session_data

    debug_log(f"DEBUG: Terminating session {session_id}. Sent terminate signal.")

    try:
        process.terminate()
        process.wait(timeout=5)
        debug_log(f"DEBUG: Session {session_id} terminated successfully and cleaned up resources.")
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        debug_log(f"DEBUG: Forced termination signal sent to session {session_id}.")
    except Exception as e:
        debug_log(f"DEBUG: Failed to terminate session {session_id}: {e}")
    finally:
        os.close(master_fd)
        debug_log(f"DEBUG: Cleaned up resources for session {session_id}.")

    # Reset the seek position for the session
    if session_id in session_seek_positions:
        session_seek_positions.pop(session_id)
        debug_log(f"DEBUG: Reset seek position for session {session_id}.")

    return f"Session {session_id} terminated successfully."

@mcp.tool()
def get_active_sessions() -> dict:
    """Retrieve a list of all active interactive sessions.

    Returns:
        dict: A dictionary containing session IDs and their statuses.
    """
    active_sessions = {}
    for session_id, (process, _) in sessions.items():
        active_sessions[session_id] = {
            "pid": process.pid,
            "status": "running" if process.poll() is None else "terminated"
        }
    return active_sessions

if __name__ == "__main__":
    if args.transport in ["sse", "streamable-http"]:
        mcp.run(transport=args.transport, port=args.port)
    else:
        mcp.run(transport=args.transport)