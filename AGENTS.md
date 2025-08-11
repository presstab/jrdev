# AGENTS.md

This document provides a guide for AI agents working with the `jrdev` codebase. It outlines the project's architecture, key components, and development conventions.

## Project Overview

`jrdev` is a command-line tool that uses AI to assist developers with various coding tasks. It's designed to be a flexible and powerful tool for AI-assisted development, with a focus on providing accurate and context-aware assistance while managing costs effectively.

### Key Features:

*   **Project Context System:** A system for maintaining a long-term, token-efficient understanding of a project's codebase.
*   **Agentic Coding Pipeline:** A multi-phase pipeline for handling code generation tasks, with opportunities for user review and intervention at each stage.
*   **Smart Model Switching:** A system for using different AI models for different tasks to balance cost and performance.
*   **Git Integration:** Commands for generating commit messages, reviewing pull requests, and more.
*   **Textual UI:** A rich terminal user interface for interacting with the tool.

## Architecture

The `jrdev` tool is built with a modular architecture, centered around a few key concepts:

*   **Application Core:** The `src/jrdev/core` directory contains the main application logic, including the `Application` class, command handling, and state management.
*   **Commands:** The `src/jrdev/commands` directory contains the implementation of all the CLI commands. Each command is a self-contained unit of functionality.
*   **Agents:** The `src/jrdev/agents` directory contains the AI agents that perform the core tasks of the tool. The `CodeAgent` is responsible for code generation, while the `RouterAgent` is responsible for interpreting natural language commands.
*   **Project Context System:** This system is responsible for maintaining a long-term understanding of the project. It is implemented in the `src/jrdev/services/contextmanager.py` file and the associated commands in `src/jrdev/commands/projectcontext.py`. The context itself is stored in the `.jrdev` directory at the root of the project.
*   **Prompts:** The `src/jrdev/prompts` directory contains all the prompts used to interact with the LLMs. This separation of prompts from code makes it easy to modify and experiment with different prompting strategies.
*   **Services:** The `src/jrdev/services` directory contains services for interacting with external APIs, such as the LLM providers and web search.
*   **UI:** The `src/jrdev/ui` directory contains the user interface code, with both a command-line interface (`cli`) and a Textual-based terminal user interface (`tui`).

## The `code` Command

The `/code` command is the core feature of `jrdev`. It uses a multi-phase agentic pipeline to handle code generation tasks. This pipeline is designed to be robust, transparent, and cost-effective.

### The `code` Command Pipeline

The pipeline consists of the following phases:

1.  **Analyze Phase:** The agent analyzes the user's request, gathers initial context from the Project Context System, and identifies the files needed to complete the task.
2.  **Fetch Context Phase:** The agent fetches the content of the identified files and any additional context provided by the user.
3.  **Plan Phase:** The agent creates a step-by-step plan for completing the task. This plan is presented to the user for review and approval.
4.  **Execute Phase:** The agent executes the plan, making changes to the files as required. The user is prompted to confirm each change.
5.  **Review Phase:** The agent reviews the changes to ensure they meet the original request.
6.  **Validate Phase:** The agent performs a final validation of the code to ensure it is syntactically correct and well-formed.

This phased approach allows for smart model switching at each step, using more powerful and expensive models only when necessary. It also provides multiple opportunities for the user to intervene, review, and guide the agent.

## Development

### Setup

To set up the development environment, clone the repository and install the dependencies in editable mode:

```bash
git clone https://github.com/presstab/jrdev
cd jrdev
pip install -e .
```

### Testing

To run the tests, use `pytest`:

```bash
pytest
```

### Linting and Formatting

This project uses `pylint` for linting, `mypy` for type checking, `black` for formatting, and `isort` for import sorting. You can run them as follows:

```bash
pylint src/
mypy src/
black src/
isort src/ tests/
```
