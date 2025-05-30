#!/usr/bin/env python3

"""
Model command implementation for the JrDev terminal.
"""
from typing import List
from jrdev.ui.ui import PrintType
from jrdev.models.model_utils import ignore_model, get_ignored_model_names, unignore_model


async def handle_model(app, args: List[str], worker_id: str):
    """
    Handle the /model command to change or display the current model.

    Args:
        app: The Application instance
        args: Command arguments /model <ignore/unignore/list-ignored/list-all> <model_name>
    """

    model_names = app.get_model_names()
    
    if len(args) > 1:
        subcommand = args[1]
        if subcommand == "list-ignored":
            ignored_str = ""
            for m in get_ignored_model_names():
                ignored_str += f"{m}\n"
            if ignored_str:
                app.ui.print_text(ignored_str)
            else:
                app.ui.print_text(f"ignored list empty")
            return
        elif subcommand == "list-all":
            all_str = "models:\n"
            for m in model_names:
                all_str += f"{m}\n"
            ignored_list = get_ignored_model_names()
            if ignored_list:
                all_str += "ignored:\n"
                for m in ignored_list:
                    all_str += f"{m}"
            app.ui.print_text(all_str)
            return

        if len(args) > 2:
            model_name = args[2]
            if subcommand == "ignore":
                if ignore_model(model_name):
                    app.ui.print_text(f"{model_name} ignored")
                else:
                    app.ui.print_text(f"failed to ignore {model_name}")
                return
            elif subcommand == "unignore":
                if model_name in get_ignored_model_names():
                    if unignore_model(model_name):
                        app.ui.print_text(f"unignored {model_name}")
                    else:
                        app.ui.print_text(f"failed to unignore {model_name}")
                else:
                    app.ui.print_text(f"{model_name} not in list of ignored names")
                return
            elif subcommand == "set":
                if model_name in model_names:
                    app.set_model(model_name)
                    app.ui.print_text(f"Model changed to: {app.state.model}", print_type=PrintType.SUCCESS)
                else:
                    app.ui.print_text(f"Unknown model: {model_name}", print_type=PrintType.ERROR)
                    app.ui.print_text(f"Available models: {', '.join(model_names)}", print_type=PrintType.INFO)
                return

    app.ui.print_text(f"Current model: {app.state.model}", print_type=PrintType.INFO)
    app.ui.print_text(f"Available models: {', '.join(model_names)}", print_type=PrintType.INFO)
    app.ui.print_text("Usage: /model <set/ignore/unignore/list-ignored/list-all> <model_name>", print_type=PrintType.INFO)
