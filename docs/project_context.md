# Project Context System

The Project Context System is a key feature of JrDev that provides long-term, token-efficient memory about your project's structure, conventions, and key files. This allows the AI to have a deep understanding of your codebase without having to re-read and re-analyze files for every request, which saves time and reduces token costs.

## How it Works

The system is built around two main commands: `/init` and `/projectcontext`.

### The `/init` Command

The `/init` command is the heart of the Project Context System. When you run it for the first time in a new project, it performs a comprehensive analysis of your codebase. This process involves several steps:

1.  **File Tree Analysis:** JrDev first scans your project's directory and creates a compact representation of the file tree.
2.  **File Recommendation:** This file tree is then sent to an AI model, which, guided by the `prompts/init/file_recommendation.md` prompt, identifies up to 20 of the most critical files in your project. This prompt instructs the AI to look for entry points, core logic, configuration files, and other architecturally significant files.
3.  **File Summarization:** For each of the recommended files, JrDev generates a dense, machine-readable summary using the `prompts/init/file_analysis.md` prompt. These summaries are optimized for consumption by other LLMs and are not meant to be human-readable. They are stored in the `.jrdev/context/` directory.
4.  **Convention Generation:** JrDev then uses the file tree and the content of the recommended files to generate a `jrdev_conventions.md` file in the `.jrdev` directory. This file, guided by the `prompts/init/project_conventions.md` prompt, outlines the project's high-level coding conventions, architecture, build process, and more.
5.  **Overview Generation:** Finally, using the file tree, the generated conventions, and all the file summaries, JrDev creates a `jrdev_overview.md` file in the `.jrdev` directory. This file, guided by the `prompts/init/project_overview.md` prompt, provides a high-level, three-paragraph conceptual overview of the project.

### The `/projectcontext` Command

The `/projectcontext` command provides a way to manage the project context after it has been initialized. It allows you to:

*   **Turn context on or off:** `/projectcontext on|off`
*   **View the status:** `/projectcontext status` shows if the context is enabled, how many files are tracked, and how many are outdated.
*   **List tracked files:** `/projectcontext list`
*   **View a file's summary:** `/projectcontext view <filepath>`
*   **Update outdated files:** `/projectcontext update`
*   **Force a refresh:** `/projectcontext refresh <filepath>`
*   **Manually add or remove files:** `/projectcontext add <filepath>` and `/projectcontext remove <filepath>`

## The `.jrdev` Directory

The `.jrdev` directory is created at the root of your project and stores all the data for the Project Context System. Here's a breakdown of its contents:

*   **`jrdev_conventions.md`:** A markdown file containing the high-level conventions of your project.
*   **`jrdev_overview.md`:** A markdown file containing a conceptual overview of your project.
*   **`context/`:** This directory contains the machine-readable summaries of your project's key files. Each summary is stored in a file with a name derived from the original file's path.
*   **`index.json`:** This file keeps track of all the files in the project context, their last modification times, and the path to their summary file.

## Usage in the Agent Pipeline

The Project Context System is a critical component of the `/code` agent's pipeline, specifically during the **Analyze Phase**. When a coding task is initiated, the `AnalyzePhase` is the first step in the pipeline. It's responsible for interpreting the user's request and identifying the necessary files to complete the task.

To do this effectively, the `AnalyzePhase` loads the following information from the Project Context System:

*   **Project Overview:** The high-level conceptual overview of the project from `.jrdev/jrdev_overview.md`.
*   **Project Conventions:** The coding conventions and architectural patterns from `.jrdev/jrdev_conventions.md`.
*   **File Summaries:** The dense, machine-readable summaries of key files from the `.jrdev/context/` directory.

This information provides the agent with a comprehensive understanding of the project's architecture, conventions, and key components. This allows the agent to make more intelligent decisions about which files are relevant to the user's request, leading to more accurate file recommendations and a higher chance of success in completing the coding task.

### Router Agent

The Router Agent, which is responsible for interpreting natural language commands and routing them to the correct tool, also uses a portion of the Project Context System. When you type a command without a leading `/`, the Router Agent is invoked.

The Router Agent includes the **Project Overview** (`.jrdev/jrdev_overview.md`) in its prompt to the AI model. This helps the model to better understand the user's intent in the context of the current project, leading to more accurate command routing.

### Git PR Review

When you use the `/git pr review` command, the full project context (overview, conventions, and file summaries) is included in the prompt to the AI model. This allows the AI to perform a more thorough and context-aware code review, taking into account your project's specific conventions and architecture.

### Chat

When you start a new chat conversation (i.e., there is no previous message history in the current thread), and the project context is enabled, the full project context is included in the first message to the LLM. This provides the AI with a strong foundation for the conversation, allowing it to answer questions and provide assistance that is tailored to your project.

By using this system, JrDev can maintain a rich, persistent understanding of your project, leading to more accurate and efficient AI assistance.
