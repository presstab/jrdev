import argparse
import asyncio
from jrdev.ui.cli.cli_app import CliApp
from .ui.ui import terminal_print, PrintType

def run_cli():
    """Entry point for console script"""
    parser = argparse.ArgumentParser(description="JrDev Terminal - LLM model interface")
    parser.add_argument("--version", action="store_true", help="Show version information")
    args = parser.parse_args()

    if args.version:
        terminal_print("JrDev Terminal v0.1.0", PrintType.INFO)
        return

    try:
        asyncio.run(CliApp().run())
    except KeyboardInterrupt:
        terminal_print("\nExiting JrDev terminal...", PrintType.INFO)

if __name__ == "__main__":
    run_cli()
