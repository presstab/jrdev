import os
import shlex
from pathlib import Path

# Correct import path based on the terminal-bench documentation
from terminal_bench.agents.installed_agents.abstract_installed_agent import (
    AbstractInstalledAgent,
)
from terminal_bench.terminal.models import TerminalCommand
from terminal_bench.agents.base_agent import AgentResult
from terminal_bench.terminal.tmux_session import TmuxSession


class JrdevAgent(AbstractInstalledAgent):
    """
    An agent implementation for running jrdev within the terminal-bench framework.
    This class provides the necessary hooks for installation and execution.
    """

    @staticmethod
    def name() -> str:
        """Define a unique name for the agent."""
        return "jrdev-cli"

    def __init__(self, *args, **kwargs):
        """
        Initialize the agent. jrdev manages models internally, so we don't
        need to pass specific model names during initialization.
        """
        super().__init__(*args, **kwargs)

    @property
    def _env(self) -> dict[str, str]:
        """
        Specifies the environment variables required by jrdev. It reads API keys
        from the host machine's environment and forwards them to the container.
        """
        # jrdev's `core/clients.py` looks for these specific environment variables.
        required_keys = [
            #"OPENAI_API_KEY",
            #"ANTHROPIC_API_KEY",
            "OPEN_ROUTER_KEY"
            # Add any other API keys your jrdev setup is configured to use.
        ]

        env_vars = {}
        for key in required_keys:
            value = os.getenv(key)
            if not value:
                # Optional: Raise an error if a required key is missing
                # raise ValueError(f"Environment variable {key} is not set on the host.")
                print(f"Warning: Environment variable {key} is not set. The agent may not function correctly.")
            else:
                env_vars[key] = value

        return env_vars

    @property
    def _install_agent_script_path(self) -> os.PathLike:
        """
        Returns the local path to the script that will install the agent.
        The harness copies this script into the task container and runs it.
        """
        # This script is expected to be in the same directory as this Python file.
        return Path(__file__).parent / "install_jrdev.sh"

    def perform_task(self, instruction: str, session: TmuxSession, logging_dir: Path = None) -> AgentResult:
        """
        Executes jrdev with the given task instruction.
        """
        # First, create the .env file with the API key
        open_router_key = os.getenv("OPEN_ROUTER_KEY", "")
        
        # Create the .jrdev directory and .env file
        setup_commands = [
            TerminalCommand(
                command="mkdir -p ~/.jrdev",
                max_timeout_sec=30.0,
                block=True,
            ),
            TerminalCommand(
                command=f"echo 'OPEN_ROUTER_KEY={open_router_key}' > ~/.jrdev/.env",
                max_timeout_sec=30.0,
                block=True,
            )
        ]
        
        # Execute setup commands
        for cmd in setup_commands:
            session.send_command(cmd)
        
        # Use shlex.quote to safely handle instructions with spaces or special characters.
        escaped_instruction = shlex.quote(instruction)

        # The command invokes the `jrdev-cli` entry point defined in setup.py.
        # jrdev's internal RouterAgent will interpret the natural language instruction.
        command_string = f"jrdev-cli --accept-all {escaped_instruction}"

        terminal_command = TerminalCommand(
            command=command_string,
            max_timeout_sec=float("inf"),  # Run until the agent process finishes.
            block=True,  # Wait for the agent to finish before the harness continues.
        )
        
        # Execute the command in the session
        session.send_command(terminal_command)
        
        # Return success result
        return AgentResult(success=True)

    def _run_agent_commands(self, task_description: str) -> list[TerminalCommand]:
        """
        Constructs the command to execute jrdev with the given task instruction.
        """
        # Use shlex.quote to safely handle instructions with spaces or special characters.
        escaped_description = shlex.quote(task_description)

        # The command invokes the `jrdev-cli` entry point defined in setup.py.
        # jrdev's internal RouterAgent will interpret the natural language instruction.
        command_string = f"jrdev-cli --accept-all {escaped_description}"

        return [
            TerminalCommand(
                command=command_string,
                max_timeout_sec=float("inf"),  # Run until the agent process finishes.
                block=True,  # Wait for the agent to finish before the harness continues.
            )
        ]