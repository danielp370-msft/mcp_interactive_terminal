# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp",
# ]
# ///
import unittest
from interactive.server import start_session, wait_for_output_or_prompt, send_command, exit_session, get_active_sessions, sessions, capture_output
import os
import tempfile
import time

class TestInteractiveTerminalServer(unittest.TestCase):

    def test_echo_interactive_session(self):
        """Test starting a simple echo session and verifying output capture."""
        # Start a simple echo session
        start_response = start_session(command="echo", args=["Hello, World!"])
        self.assertIsInstance(start_response, str, "start_session should return a string")
        self.assertIn("Session", start_response, "start_session response should contain 'Session'")

        # Extract session ID from the start response
        session_id = int(start_response.split()[1])

        # Wait for the echo output
        wait_response = wait_for_output_or_prompt(session_id=session_id, prompts=["Hello, World!"], timeout=5)
        self.assertIsInstance(wait_response, str, "wait_for_output_or_prompt should return a string")
        self.assertIn("Hello, World!", wait_response, "wait_for_output_or_prompt response should contain the echo output")

        # Exit the session
        exit_response = exit_session(session_id=session_id)
        self.assertIsInstance(exit_response, str, "exit_session should return a string")
        self.assertIn("terminated", exit_response, "exit_session response should confirm termination")

    def test_python_interactive_session(self):
        """Test starting a Python interactive session and sending commands."""
        print("TEST: Starting Python interactive session test")

        # Start a Python interactive session
        start_response = start_session(command="python3", args=["-i"])
        print("TEST: Started session")
        self.assertIsInstance(start_response, str, "start_session should return a string")
        self.assertIn("Session", start_response, "start_session response should contain 'Session'")

        # Extract session ID from the start response
        session_id = int(start_response.split()[1])
        print(f"TEST: Extracted session ID: {session_id}")

        # Wait for the Python prompt
        wait_response = wait_for_output_or_prompt(session_id=session_id, prompts=[">>>"], timeout=5)
        print(f"TEST: Wait response: {wait_response}")  # Debugging output
        print("TEST: Detected Python prompt")
        self.assertIsInstance(wait_response, str, "wait_for_output_or_prompt should return a string")
        self.assertIn(">>>", wait_response, "wait_for_output_or_prompt response should contain the Python prompt")

        # Send a Python command
        send_response = send_command(session_id=session_id, command="print(42)")
        print("TEST: Sent command to Python session")
        self.assertIsInstance(send_response, str, "send_command should return a string")
        self.assertIn("success", send_response, "send_command response should confirm success")

        # Wait for the output of the command
        wait_response = wait_for_output_or_prompt(session_id=session_id, prompts=["42"], timeout=5)
        print("TEST: Detected output of the command")
        self.assertIsInstance(wait_response, str, "wait_for_output_or_prompt should return a string")
        self.assertIn("42", wait_response, "wait_for_output_or_prompt response should contain the command output")

        # Exit the session
        exit_response = exit_session(session_id=session_id)
        print("TEST: Exited Python session")
        self.assertIsInstance(exit_response, str, "exit_session should return a string")
        self.assertIn("terminated", exit_response, "exit_session response should confirm termination")

        print("TEST: Completed Python interactive session test")

class TestInteractiveServer(unittest.TestCase):

    def test_get_active_sessions(self):
        # Start a new session
        session_id_message = start_session("python3", [])
        self.assertIn("Session", session_id_message)
        session_id = int(session_id_message.split()[1])

        # Check active sessions
        active_sessions = get_active_sessions()
        self.assertIn(session_id, active_sessions)
        self.assertEqual(active_sessions[session_id]["status"], "running")

        # Exit the session
        exit_message = exit_session(session_id)
        self.assertIn("terminated successfully", exit_message)

        # Verify session is no longer active
        active_sessions = get_active_sessions()
        self.assertNotIn(session_id, active_sessions)

class TestServer(unittest.TestCase):

    def test_start_session_with_log_file(self):
        """Test starting a session with a log file set."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_log_file:
            log_file_path = temp_log_file.name

        try:
            # Start a session with a log file
            response = start_session("echo", ["Hello, World!"], log_file=log_file_path)
            self.assertIn("Session", response)

            # Extract session ID from the response
            session_id = int(response.split()[1])
            self.assertIn(session_id, sessions)

            # Trigger output capture manually to ensure log file is written
            process, master_fd, _, _, _, log_file = sessions[session_id]
            os.write(master_fd, b"\n")  # Send a newline to flush output
            time.sleep(0.1)  # Allow time for output to be captured

            # Manually trigger output capture
            capture_output(master_fd, session_id)

            # Verify the log file is set correctly
            self.assertEqual(log_file, log_file_path)

            # Verify the log file contains the expected output
            with open(log_file_path, "r") as log_file:
                log_content = log_file.read()
                self.assertIn("Hello, World!", log_content)
        finally:
            # Clean up the temporary log file
            os.remove(log_file_path)

if __name__ == "__main__":
    unittest.main()