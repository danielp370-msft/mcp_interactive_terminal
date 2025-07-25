# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp",
# ]
# ///
import os
import argparse
import subprocess
import time
import pty
import atexit
import signal
import datetime
import fcntl  # Ensure fcntl is imported for non-blocking I/O
from fastmcp import FastMCP
import asyncio

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
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Interactive Terminal Server 🖥️")
    parser.add_argument("--transport", type=str, default="stdio", choices=["stdio", "sse", "streamable-http"], help="Transport type (default: stdio, supports: stdio, sse, streamable-http)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port number for SSE or streamable-http transport (default: {DEFAULT_PORT})")
    args = parser.parse_args()

# Session timeout config (seconds)
SESSION_TIMEOUT = int(os.environ.get("MCP_SESSION_TIMEOUT", 3600))  # default 1 hour

sessions = {}  # session_id: (process, master_fd, shared_buffer, seek_position, search_pos, log_file, last_activity)

# Ensure all subprocesses are terminated on program exit
def cleanup_sessions():
    for session_id, (process, master_fd, _, _, _, _, _) in list(sessions.items()):
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
def capture_output(master_fd, session_id, buffer_size=4096):
    try:
        # Set the file descriptor to non-blocking mode
        fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)
        output = os.read(master_fd, buffer_size).decode()
        debug_log(f"DEBUG: Captured output: {output}")

        # Check if the session has a log_file set
        process, master_fd, shared_buffer, seek_position, search_pos, log_file, _ = sessions[session_id]
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

def advance_session_buffer_to_end(session_id):
    """Advance seek and search positions to the end of the buffer for the given session, after capturing any new output."""
    process, master_fd, shared_buffer, seek_position, search_pos, log_file, _ = sessions[session_id]
    # Capture any new output before advancing
    new_data = capture_output(master_fd, session_id)
    if new_data:
        shared_buffer += new_data
    seek_position = len(shared_buffer)
    search_pos = len(shared_buffer)
    sessions[session_id] = (process, master_fd, shared_buffer, seek_position, search_pos, log_file, _now())

# Async session cleanup coroutine
def _terminate_session(session_id):
    session_data = sessions.pop(session_id, None)
    if not session_data:
        return
    process, master_fd, *_ = session_data
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except Exception:
            pass
    finally:
        try:
            os.close(master_fd)
        except Exception:
            pass

def _refresh_last_activity(session_id):
    if session_id in sessions:
        sess = list(sessions[session_id])
        sess[-1] = _now()
        sessions[session_id] = tuple(sess)

async def session_cleanup_task():
    while True:
        now = _now()
        to_terminate = [sid for sid, sess in sessions.items() if now - sess[-1] > SESSION_TIMEOUT]
        for sid in to_terminate:
            _terminate_session(sid)
        await asyncio.sleep(60)

# Updated start_session function to include log_file in session structure and clear log file if specified
async def _start_session(command: str, args: list, log_file: bool = True) -> str:
    """Start a new interactive session for a program.

    Parameters:
        command (str): The command to start the interactive session (e.g., 'python').
        args (list): A list of arguments to pass to the command.
        log_file (bool): Whether to create a log file for the session output. Defaults to True.

    Returns:
        str: A message indicating the session ID if successful, or an error message if the session could not be started.
    """
    session_id = len(sessions) + 1

    log_file_path = None
    if log_file:
        # Use the base name of the command (no path), and a date string
        base_cmd = os.path.basename(command)
        date_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file_path = f"crash-analysis-log-{base_cmd}-{date_str}.log"
        try:
            with open(log_file_path, "w") as log:
                log.write("")
        except Exception:
            log_file_path = None  # Fallback: no log file if creation fails

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
    sessions[session_id] = (process, master_fd, "", 0, 0, log_file_path, _now())

    return f"Session {session_id} started. Log file: {log_file_path if log_file_path else 'None'}"

start_session = mcp.tool()(_start_session)

async def _wait_for_output_or_prompt(session_id: int, prompts: list, timeout: int = 5, return_output: bool = True, consume_post_prompt_whitespace: bool = True) -> dict:
    """Wait for specific output, a prompt, or gather output within a timeout.

    Parameters:
        session_id (int): The ID of the session to monitor.
        prompts (list): A list of strings to detect in the output (e.g., prompts or specific text).
        timeout (int, optional): The maximum time to wait for the output, in seconds. Defaults to 5.
        return_output (bool, optional): Whether to return the captured output until timeout or prompt is reached. Defaults to True.
        consume_post_prompt_whitespace (bool, optional): If True, consume whitespace after the prompt in the output buffer. Defaults to True.

    Returns:
        dict: Structured output with status, prompt (if found), captured_output, remaining_bytes, and message.
    """
    _refresh_last_activity(session_id)
    if session_id not in sessions:
        debug_log("DEBUG: Invalid session ID.")
        return {
            "status": "error",
            "message": "Invalid session ID."
        }
    process, master_fd, shared_buffer, seek_position, search_pos, log_file, _ = sessions[session_id]
    start_time = time.time()
    start_pos = seek_position
    while time.time() - start_time < timeout:
        new_data = capture_output(master_fd, session_id)
        if new_data:
            shared_buffer += new_data
            sessions[session_id] = (process, master_fd, shared_buffer, seek_position, search_pos, log_file, _now())
        else:
            time.sleep(0.1)
        debug_log(f"DEBUG: Accumulated data for session {session_id}: {shared_buffer}")
        for prompt in prompts:
            prompt_index = shared_buffer.find(prompt, search_pos)
            if prompt_index != -1:
                debug_log(f"DEBUG: Prompt '{prompt}' detected for session {session_id} at position {prompt_index}.")
                seek_position = prompt_index + len(prompt)
                if consume_post_prompt_whitespace:
                    whitespace_end = seek_position
                    while whitespace_end < len(shared_buffer) and shared_buffer[whitespace_end] in (' ', '\t', '\r', '\n'):
                        whitespace_end += 1
                    if whitespace_end > seek_position:
                        debug_log(f"DEBUG: Consuming post-prompt whitespace for session {session_id} from {seek_position} to {whitespace_end}.")
                        seek_position = whitespace_end
                search_pos = seek_position
                sessions[session_id] = (process, master_fd, shared_buffer, seek_position, search_pos, log_file, _now())
                remaining_bytes = len(shared_buffer) - seek_position
                captured_output = shared_buffer[start_pos:seek_position] if return_output else None
                return {
                    "status": "prompt_detected",
                    "prompt": prompt,
                    "captured_output": captured_output,
                    "remaining_bytes": remaining_bytes,
                    "message": f"To get to get remaining bytes available after prompt, call this again."
                }
    debug_log(f"DEBUG: Timeout reached for session {session_id}.")
    seek_position = len(shared_buffer)
    sessions[session_id] = (process, master_fd, shared_buffer, seek_position, search_pos, log_file, _now())
    captured_output = shared_buffer[start_pos:seek_position] if return_output else None
    if captured_output and len(captured_output) > 0:
        return {
            "status": "prompt_timeout_with_bytes_received",
            "prompt": None,
            "captured_output": captured_output,
            "remaining_bytes": 0,
            "message": "Timeout reached without detecting any specified prompt, but bytes were received. Check output and consider calling again."
        }
    else:
        return {
            "status": "prompt_timeout_no_bytes_received",
            "prompt": None,
            "captured_output": captured_output,
            "remaining_bytes": 0,
            "message": "Timeout reached without detecting any specified prompt and no bytes were received."
        }

wait_for_output_or_prompt = mcp.tool()(_wait_for_output_or_prompt)

async def _send_command(session_id: int, command: str, send_newline: bool = True, preflush: bool = True) -> str:
    """Send a command to the interactive session.

    Parameters:
        session_id (int): The ID of the session to send the command to.
        command (str): The command to send to the session. If send_newline is True, a newline will be appended automatically.
        send_newline (bool, optional): If True, append a newline to the command before sending. Defaults to True.
        preflush (bool, optional): If True, skip over any unread contents of the output buffer pointers before sending the command. Defaults to True.
    Returns:
        str: A message indicating success or failure of sending the command.
    """
    _refresh_last_activity(session_id)
    session_data = sessions.get(session_id)
    if not session_data:
        return "Invalid session ID."
    if preflush:
        advance_session_buffer_to_end(session_id)
        session_data = sessions[session_id]
    process, master_fd, shared_buffer, seek_position, search_pos, log_file, _ = session_data
    try:
        to_send = command + ('\n' if send_newline else '')
        os.write(master_fd, to_send.encode())
        return "Command sent successfully."
    except OSError as e:
        return f"Failed to send command: {e}"

send_command = mcp.tool()(_send_command)

async def _exit_session(session_id: int) -> str:
    """Terminate and clean up the interactive session.

    Parameters:
        session_id (int): The ID of the session to terminate.

    Returns:
        str: A message indicating the session termination status or an error message if termination failed.
    """
    _refresh_last_activity(session_id)
    session_data = sessions.pop(session_id, None)
    if not session_data:
        return "Invalid session ID."
    process, master_fd, _, _, _, _, _ = session_data
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

exit_session = mcp.tool()(_exit_session)

async def _get_active_sessions() -> dict:
    """Retrieve a list of all active interactive sessions.

    Returns:
        dict: A dictionary containing session IDs and their statuses.
    """
    active_sessions = {}
    for session_id, (process, _, _, _, _, _, _) in sessions.items():
        active_sessions[session_id] = {
            "pid": process.pid,
            "status": "running" if process.poll() is None else "zombie"
        }
    return active_sessions

get_active_sessions = mcp.tool()(_get_active_sessions)

def _now():
    return int(time.time())

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(session_cleanup_task())
    if args.transport in ["sse", "streamable-http"]:
        mcp.run(transport=args.transport, port=args.port)
    else:
        mcp.run(transport=args.transport)