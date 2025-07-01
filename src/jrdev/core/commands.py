import os
from typing import Dict, Callable, Any, List

from jrdev.commands import (
    handle_addcontext,
    handle_asyncsend,
    handle_cancel,
    handle_clearcontext,
    handle_code,
    handle_compact,
    handle_cost,
    handle_exit,
    handle_git,
    handle_help,
    handle_init,
    handle_keys,
    handle_migrate,
    handle_model,
    handle_models,
    handle_modelprofile,
    handle_projectcontext,
    handle_provider,
    handle_routeragent,
    handle_stateinfo,
    handle_tasks,
    handle_thread,
    handle_viewcontext
)

class Command:
    def __init__(self, _text, _id):
        self.text = _text
        self.request_id = _id

class CommandHandler:
    """Manage command registration and execution"""

    def __init__(self, app: Any):
        self.app = app
        self.commands: Dict[str, Callable] = {}
        self._register_core_commands()

    def _register_core_commands(self) -> None:
        """Register all core command handlers"""
        core_commands = {
            "/exit": handle_exit,
            "/model": handle_model,
            "/models": handle_models,
            "/modelprofile": handle_modelprofile,
            "/stateinfo": handle_stateinfo,
            "/clearcontext": handle_clearcontext,
            "/compact": handle_compact,
            "/cost": handle_cost,
            "/init": handle_init,
            "/help": handle_help,
            "/addcontext": handle_addcontext,
            "/viewcontext": handle_viewcontext,
            "/asyncsend": handle_asyncsend,
            "/tasks": handle_tasks,
            "/cancel": handle_cancel,
            "/code": handle_code,
            "/projectcontext": handle_projectcontext,
            "/git": handle_git,
            "/keys": handle_keys,
            "/provider": handle_provider,
            "/routeragent": handle_routeragent,
            "/thread": handle_thread,
            "/migrate": handle_migrate
        }

        self.commands.update(core_commands)

        if os.getenv("JRDEV_DEBUG"):
            self._register_debug_commands()

    def _register_debug_commands(self) -> None:
        """Register debug-specific commands"""
        from jrdev.commands.debug import handle_modelswin
        self.commands["/modelswin"] = handle_modelswin

    async def execute(self, command: str, args: List[str], worker_id: str) -> Any:
        """
        Execute a command with arguments
        Args:
            command: The command string (e.g. "/model")
            args: List of arguments including the command itself
            worker_id: ID of worker/task
        Returns:
            Result of the command handler execution
        """
        cmd = command.split()[0].lower() if command else ""
        handler = self.commands.get(cmd)

        if not handler:
            self.app.logger.warning(f"Unknown command: {cmd}")
            return None

        try:
            return await handler(self.app, args, worker_id)
        except Exception as e:
            self.app.logger.error(f"Error executing command {cmd}: {str(e)}")
            raise

    def register_command(self, command: str, handler: Callable) -> None:
        """Register a new command handler"""
        if not command.startswith("/"):
            command = f"/{command}"
        self.commands[command.lower()] = handler

    def deregister_command(self, command: str) -> None:
        """Remove a command handler"""
        cmd = command.lower()
        if cmd in self.commands:
            del self.commands[cmd]

    def get_commands(self) -> Dict[str, Callable]:
        """Get all registered commands"""
        return self.commands.copy()
