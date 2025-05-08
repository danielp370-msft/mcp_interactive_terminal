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
import fcntl  # Ensure fcntl is imported for non-blocking I/O

# Add a debug macro-like function
DEBUG_MODE = False  # Set debug mode to false
GLOBAL_DEBUG_LOG_FILE = "./debug.log"  # Update log file path to a relative location

def debug_log(message):
    if DEBUG_MODE:
        print(message, flush=True)
        with open(GLOBAL_DEBUG_LOG_FILE, "a") as log_file:
            log_file.write(f"{message}\n")

mcp = FastMCP("Interactive Terminal Server 🖥️")

# Parse command-line arguments
DEFAULT_PORT = 8070
parser = argparse.ArgumentParser(description="Run the Interactive Terminal Server 🖥️")
parser.add_argument("--transport", type=str, default="stdio", choices=["stdio", "sse", "streamable-http"], help="Transport type (default: stdio, supports: stdio, sse, streamable-http)")
parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port number for SSE or streamable-http transport (default: {DEFAULT_PORT})")
args = parser.parse_args()

sessions = {}

# Ensure all subprocesses are terminated on program exit
def cleanup_sessions():
    for session_id, (process, master_fd, _, _, _, _) in list(sessions.items()):
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            debug_log(f"DEBUG: Cleanup - Terminated session {session_id}.")
        except Exception as e:
            debug_log(f"DEBUG: Cleanup - Failed to terminate session {session_id}: {e}")
        finally:
            os.close(master_fd)
            debug_log(f"DEBUG: Cleanup - Closed master_fd for session {session_id}.")

atexit.register(cleanup_sessions)

# Updated capture_output function to accept session_id and write output to log file if set
def capture_output(master_fd, session_id, buffer_size=1024):
    try:
        # Set the file descriptor to non-blocking mode
        fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)
        output = os.read(master_fd, buffer_size).decode()
        debug_log(f"DEBUG: Captured output: {output}")

        # Check if the session has a log_file set
        process, master_fd, shared_buffer, seek_position, search_pos, log_file = sessions[session_id]
        if log_file:
            debug_log(f"DEBUG: Writing to log file: {log_file}")
            debug_log(f"DEBUG: Output being written: {output}")
            with open(log_file, "a") as log:
                log.write(output)
                log.flush()

        return output
    except BlockingIOError:
        # No data available, return an empty string
        return ""

# Updated start_session function to include log_file in session structure and clear log file if specified
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

    # Clear the log file if specified
    if log_file:
        try:
            with open(log_file, "w") as log:
                log.write("")
        except Exception:
            pass  # Ignore errors if the file does not exist or cannot be cleared

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

    # Add session with log_file always included, and search_pos initialized to 0
    sessions[session_id] = (process, master_fd, "", 0, 0, log_file)

    return f"Session {session_id} started."

# Updated wait_for_output_or_prompt function to use search_pos for scanning, and always return output from start_pos:seek_position
@mcp.tool()
def wait_for_output_or_prompt(session_id: int, prompts: list, timeout: int = 5, return_output: bool = True) -> str:
    """Wait for specific output, a prompt, or gather output within a timeout.

    Parameters:
        session_id (int): The ID of the session to monitor.
        prompts (list): A list of strings to detect in the output (e.g., prompts or specific text).
        timeout (int, optional): The maximum time to wait for the output, in seconds. Defaults to 5.
        return_output (bool, optional): Whether to return the captured output until timeout or prompt is reached. Defaults to True.

    Returns:
        str: A message indicating the detected output, or a timeout message if no match is found. If return_output is True, includes the captured output.
    """
    if session_id not in sessions:
        debug_log("DEBUG: Invalid session ID.")
        return "Invalid session ID."

    process, master_fd, shared_buffer, seek_position, search_pos, log_file = sessions[session_id]
    start_time = time.time()

    # Capture the initial seek position
    start_pos = seek_position

    while time.time() - start_time < timeout:
        new_data = capture_output(master_fd, session_id)
        if new_data:
            shared_buffer += new_data
            sessions[session_id] = (process, master_fd, shared_buffer, seek_position, search_pos, log_file)  # Update the shared buffer

        debug_log(f"DEBUG: Accumulated data for session {session_id}: {shared_buffer}")

        # Scan the buffer starting from the search position
        for prompt in prompts:
            prompt_index = shared_buffer.find(prompt, search_pos)
            if prompt_index != -1:
                debug_log(f"DEBUG: Prompt '{prompt}' detected for session {session_id} at position {prompt_index}.")
                seek_position = prompt_index + len(prompt)  # Update seek position
                search_pos = seek_position  # Advance search_pos only on match
                sessions[session_id] = (process, master_fd, shared_buffer, seek_position, search_pos, log_file)  # Persist seek and search positions
                remaining_bytes = len(shared_buffer) - seek_position
                if return_output:
                    captured_output = shared_buffer[start_pos:seek_position]
                    debug_log(f"DEBUG: Captured output for session {session_id}: {captured_output}")
                    return f"Output '{prompt}' detected. Another {remaining_bytes} bytes available after prompt. Captured output: {captured_output}"
                return f"Output '{prompt}' detected. Another {remaining_bytes} bytes available after prompt."

        time.sleep(0.1)

    debug_log(f"DEBUG: Timeout reached for session {session_id}.")
    seek_position = len(shared_buffer)  # Always advance seek_position to end
    sessions[session_id] = (process, master_fd, shared_buffer, seek_position, search_pos, log_file)  # Persist state
    if return_output:
        captured_output = shared_buffer[start_pos:seek_position]
        debug_log(f"DEBUG: Captured output on timeout for session {session_id}: {captured_output}")
        return f"Timeout reached without detecting any specified output. Captured output: {captured_output}"
    return "Timeout reached without detecting any specified output."

def advance_session_buffer_to_end(session_id):
    """Advance seek and search positions to the end of the buffer for the given session."""
    process, master_fd, shared_buffer, _, _, log_file = sessions[session_id]
    seek_position = len(shared_buffer)
    search_pos = len(shared_buffer)
    sessions[session_id] = (process, master_fd, shared_buffer, seek_position, search_pos, log_file)

@mcp.tool()
def send_command(session_id: int, command: str, preflush: bool = False) -> str:
    """Send a command to the interactive session.

    Parameters:
        session_id (int): The ID of the session to send the command to.
        command (str): The command to send to the session. Interactive shell like commands will probably want a newline character.
        preflush (bool, optional): If True, advance the output buffer pointers before sending the command. Defaults to False.
    Returns:
        str: A message indicating success or failure of sending the command.
    """
    session_data = sessions.get(session_id)
    if not session_data:
        return "Invalid session ID."

    if preflush:
        advance_session_buffer_to_end(session_id)
        session_data = sessions[session_id]
    process, master_fd, shared_buffer, seek_position, search_pos, log_file = session_data

    try:
        os.write(master_fd, (command + "\n").encode())
        return "Command sent successfully."
    except OSError as e:
        return f"Failed to send command: {e}"

@mcp.tool()
def exit_session(session_id: int) -> str:
    """Terminate and clean up the interactive session.

    Parameters:
        session_id (int): The ID of the session to terminate.

    Returns:
        str: A message indicating the session termination status or an error message if termination failed.
    """
    session_data = sessions.pop(session_id, None)
    if not session_data:
        return "Invalid session ID."

    process, master_fd, _, _, _, _ = session_data

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

    return f"Session {session_id} terminated successfully."

@mcp.tool()
def get_active_sessions() -> dict:
    """Retrieve a list of all active interactive sessions.

    Returns:
        dict: A dictionary containing session IDs and their statuses.
    """
    active_sessions = {}
    for session_id, (process, _, _, _, _, _) in sessions.items():
        active_sessions[session_id] = {
            "pid": process.pid,
            "status": "running" if process.poll() is None else "zombie"
        }
    return active_sessions

if __name__ == "__main__":
    if args.transport in ["sse", "streamable-http"]:
        mcp.run(transport=args.transport, port=args.port)
    else:
        mcp.run(transport=args.transport)