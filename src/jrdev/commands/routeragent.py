from typing import Any, List

from jrdev.ui.ui import PrintType


async def handle_routeragent(app: Any, args: List[str], _worker_id: str):
    """
    Router:Ignore
    Manages settings for the router agent, which interprets natural language requests.

    This command allows you to configure the behavior of the router agent, such as
    the maximum number of tool calls it can make for a single user request.

    Usage:
      /routeragent [subcommand] [arguments]

    Subcommands:
      (no subcommand)               - Shows the current settings and basic usage.
      clear                         - Clears the message history of the router agent
      set-max-iter <number>         - Sets the maximum number of iterations (tool calls)
                                      the router agent can perform for a single request.
                                      A reasonable range is 1-20.

    Example:
      /routeragent set-max-iter 5
    """
    if len(args) < 2:
        app.ui.print_text(
            "Manages settings for the router agent.\n"
            "Usage:\n"
            "  /routeragent set-max-iter <number> - Set max iterations for the agent.",
            print_type=PrintType.INFO,
        )
        app.ui.print_text(
            f"Current max iterations: {app.user_settings.max_router_iterations}", print_type=PrintType.INFO
        )
        return

    subcommand = args[1].lower()
    if subcommand == "clear":
        app.state.reset_router_thread()
        app.ui.print_text(f"Cleared router thread and context", print_type=PrintType.INFO)
        return

    if subcommand == "set-max-iter":
        if len(args) < 3:
            app.ui.print_text("Usage: /routeragent set-max-iter <number>", print_type=PrintType.ERROR)
            return

        try:
            new_max_iter = int(args[2])
            if not 1 <= new_max_iter <= 50:
                app.ui.print_text("Error: max iterations must be between 1 and 50.", print_type=PrintType.ERROR)
                return

            app.user_settings.max_router_iterations = new_max_iter
            app.ui.print_text(f"Router agent max iterations set to {new_max_iter}.", print_type=PrintType.SUCCESS)
            app.write_user_settings()

        except ValueError:
            app.ui.print_text("Error: Invalid number provided for max iterations.", print_type=PrintType.ERROR)
    else:
        app.ui.print_text(f"Unknown subcommand: {subcommand}", print_type=PrintType.ERROR)
        app.ui.print_text("Usage: /routeragent set-max-iter <number>", print_type=PrintType.INFO)
