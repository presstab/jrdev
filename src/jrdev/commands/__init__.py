"""
Command implementations for the JrDev terminal.
"""

import os

from jrdev.commands.addcontext import handle_addcontext
from jrdev.commands.asyncsend import handle_asyncsend
from jrdev.commands.cancel import handle_cancel
from jrdev.commands.clearcontext import handle_clearcontext
from jrdev.commands.code import handle_code
from jrdev.commands.compact import handle_compact
from jrdev.commands.cost import handle_cost
from jrdev.commands.exit import handle_exit
from jrdev.commands.git import handle_git
from jrdev.commands.git_pr import handle_git_pr_review, handle_git_pr_summary
from jrdev.commands.help import handle_help
from jrdev.commands.init import handle_init
from jrdev.commands.keys import handle_keys
from jrdev.commands.migrate import handle_migrate
from jrdev.commands.model import handle_model
from jrdev.commands.modelprofile import handle_modelprofile
from jrdev.commands.models import handle_models
from jrdev.commands.projectcontext import handle_projectcontext
from jrdev.commands.provider import handle_provider
from jrdev.commands.routeragent import handle_routeragent
from jrdev.commands.stateinfo import handle_stateinfo
from jrdev.commands.tasks import handle_tasks
from jrdev.commands.thread import handle_thread
from jrdev.commands.viewcontext import handle_viewcontext

__all__ = [
    "handle_addcontext",
    "handle_asyncsend",
    "handle_cancel",
    "handle_code",
    "handle_compact",
    "handle_cost",
    "handle_exit",
    "handle_git",
    "handle_git_pr_summary",
    "handle_git_pr_review",
    "handle_help",
    "handle_init",
    "handle_keys",
    "handle_migrate",
    "handle_model",
    "handle_models",
    "handle_modelprofile",
    "handle_projectcontext",
    "handle_provider",
    "handle_routeragent",
    "handle_stateinfo",
    "handle_tasks",
    "handle_thread",
    "handle_viewcontext",
    "handle_clearcontext",
]

# Debug commands
if os.getenv("JRDEV_DEBUG"):  # Only include in debug mode
    from jrdev.commands.debug import (
        handle_git_debug_config_dump,
        handle_modelswin,
    )

    __all__ += ["handle_modelswin", "handle_git_debug_config_dump"]
