import argparse
import asyncio
import sys
from jrdev.core.application import Application
from jrdev.ui.cli.cli_app import CliApp
from jrdev.ui.cli_events import CliEvents
from .ui.ui import terminal_print, PrintType
from jrdev.agents.code_agent import CodeAgent


def run_cli():
    """
    Entry point for the console script.
    Supports both interactive REPL mode and one-shot execution for benchmarks.
    """
    parser = argparse.ArgumentParser(
        description="JrDev Terminal - An AI-powered development assistant."
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information and exit."
    )
    # Add a positional argument to capture the instruction for one-shot mode.
    # nargs='*' will collect all positional arguments into a list.
    parser.add_argument(
        "instruction",
        nargs='*',
        help="The instruction to execute in non-interactive mode. If not provided, starts the REPL."
    )
    parser.add_argument(
        "--accept-all",
        action="store_true",
        help="Automatically accept all code change confirmations."
    )
    args = parser.parse_args()

    if args.version:
        # The version is defined in CliApp, but we can hardcode it or get it from __version__
        from jrdev import __version__
        terminal_print(f"JrDev Terminal v{__version__}", PrintType.INFO)
        return

    if args.accept_all:
        original_init = CodeAgent.__init__
        def new_init(self, *init_args, **init_kwargs):
            original_init(self, *init_args, **init_kwargs)
            self.accept_all_active = True
        CodeAgent.__init__ = new_init

    # --- Main Logic: Decide between one-shot or REPL mode ---
    if args.instruction:
        # --- ONE-SHOT MODE ---
        # An instruction was provided. Run it and exit.
        full_instruction = " ".join(args.instruction)

        # We need an async function to run the core application logic.
        async def run_one_shot_task(instruction_text: str):
            """Initializes the app, processes a single input, and exits."""
            app = Application(ui_mode="cli")  # Use the CLI UI for simple stdout
            app.ui = CliEvents(app)
            app.setup()

            # Initialize services like API clients
            if not await app.initialize_services():
                print("Error: Failed to initialize application services.", file=sys.stderr)
                sys.exit(1)

            # Process the single instruction
            await app.process_input(instruction_text, worker_id="cli-one-shot")

        try:
            asyncio.run(run_one_shot_task(full_instruction))
        except Exception as e:
            print(f"An error occurred during one-shot execution: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        # --- INTERACTIVE REPL MODE ---
        # No instruction provided. Start the interactive CliApp.
        try:
            asyncio.run(CliApp().run())
        except KeyboardInterrupt:
            terminal_print("\nExiting JrDev terminal...", PrintType.INFO)


if __name__ == "__main__":
    run_cli()
