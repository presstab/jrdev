# JrDev Terminal - AI-Powered Developer Assistant

JrDev is a powerful, AI-driven assistant designed to integrate seamlessly into your development workflow. It offers a rich Textual User Interface (TUI) for interacting with various Large Language Models (LLMs) like those from OpenAI, Anthropic, and Venice. Streamline your coding, review, and project understanding tasks directly from your terminal.

While a basic command-line interface (`jrdev-cli`) is available, the primary and recommended way to use JrDev is through its interactive TUI, launched with the `jrdev` command.

## Key Features

*   **Interactive Chat Interface**: Engage in multi-threaded conversations with AI models. Each chat maintains its own context, including selected files.
*   **Intelligent Project Initialization (`/init`)**: Makes JrDev project-aware by scanning your codebase. It indexes key files, understands the file structure, and can even infer coding conventions, all to provide the AI with a rich, token-efficient context for highly relevant assistance.
*   **Interactive AI-Powered Coding (`/code`)**: Automate and assist with code generation and modification. Describe your coding task, and JrDev collects required context (or add it yourself), then guides an AI through a multi-step process:
    *   **Planning**: The AI analyzes your request and proposes a series of steps to accomplish the task.
    *   **Review & Edit Steps**: You can review, edit, or re-prompt the AI on these steps to ensure the code task stays within scope.
    *   **Implementation**: The AI implements each step, proposing code changes.
    *   **Confirmation**: View diffs of proposed changes and approve, reject, or request revisions before any code is written to your files. Use Auto-Accept to bypass confirmations.
    *   **Validation**: The AI model performs a final review and validation of the changes.
*   **Git Integration**: Configure your base Git branch and generate PR summaries or code reviews directly within the TUI.
*   **Versatile Model Management**:
    *   Easily select from a list of available LLMs from different providers.
    *   Configure Model Profiles to assign specific models to different tasks (e.g. one model for task planning, another for complex code generation, and a different model for file indexing).
*   **Real-time Task Monitoring**: Keep an eye on ongoing AI operations, including token usage and status, with the ability to cancel tasks.
*   **Intuitive File Navigation**: Browse your project's file tree, and easily add files to the AI's context for chat or code operations.
*   **Centralized Configuration**: Manage API keys and model profiles through dedicated TUI screens.
*   **Persistent History**: Command history in the terminal input and chat history within threads are saved.

## Requirements

*   Python 3.7 or higher
*   API Keys for LLM providers (see Configuration)

## Installation

```bash
# Install from the current directory (if cloned)
pip install -e .

# Or install directly from GitHub
pip install git+https://github.com/presstab/jrdev.git
```
It's also recommended to install `requirements.txt` if you clone the repository:
```bash
pip install -r requirements.txt
```

## Configuration

### API Keys

JrDev requires at least one API key to function. Upon first launch, or by accessing the "API Keys" setting in the TUI, you'll be prompted to enter your keys. These are stored in a `.env` file in your project's root directory (JrDev will create this file if it doesn't exist).

1.  **Venice API Key** (recommended for access to a variety of models): Get your API key from [Venice](https://venice.ai)
2.  **OpenAI API Key** (optional, for OpenAI-specific models): Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
3.  **Anthropic API Key** (optional, for Anthropic models): Get your API key from [Anthropic](https://www.anthropic.com/api).
4.  **DeepSeek API Key** (optional, for DeepSeek models): Get your API key from [DeepSeek](https://deepseek.com).
5.  **OpenRouter API Key** (optional, for access to most models from one simple key): Get your API key from [OpenRouter](https://openrouter.ai).

If you would like to manually setup your `.env` file, place it within the jrdev directory.
Example `.env` file content:
```
VENICE_API_KEY=your_venice_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPEN_ROUTER_KEY=your_open_router_api_key_here
```
For convenience, an example file `.env_example` is included in the repository that you can copy and edit:
```bash
cp .env_example .env
# Then edit .env to add your actual API keys, or let JrDev TUI guide you.
```

## Running JrDev (Textual UI)

After installation, launch the JrDev TUI from your terminal:
```bash
jrdev
```
**Important:** JrDev operates within the context of the directory from which you launch it. This means all file operations, project scanning (like `/init`), and context building will be relative to your current working directory when you start the application. For best results, navigate to your project's root directory in your terminal *before* running the `jrdev` command.

**First Run:**
If no API keys are configured, JrDev will automatically open the "API Key Entry" screen. Enter your keys to proceed.

**Project Initialization:**
For the best experience, especially when working within a specific project, run the `/init` command in JrDev's terminal view. This is a crucial step that makes JrDev project-aware. It scans your project (from the directory you launched it in), identifies important files, generates summaries (like `jrdev_overview.md` for a high-level understanding and `jrdev_conventions.md` for coding patterns), and builds an indexed context. This allows the AI to understand your codebase structure and provide more accurate and relevant assistance for both chat and coding tasks.
```
> /init
```

## Understanding the Interface

The JrDev TUI is organized into three main vertical panes:

*   **Left Pane:**
    *   **Settings Buttons**:
        *   `API Keys`: Add or edit your LLM provider API keys.
        *   `Profiles`: Manage Model Profiles. Assign different AI models to specific tasks (e.g., 'chat', 'code', 'init').
        *   `Git Tools`: Configure Git settings (like base branch for diffs) and generate PR summaries or reviews.
    *   **Chat List**: Displays all your conversation threads. Click `+ New Chat` to start a new one, or click an existing thread to switch to it.

*   **Middle Pane:**
    *   **Task Monitor (Top)**: Shows active and completed AI tasks, their status, token counts, and runtime. You can stop all active tasks using the "Stop Tasks" button.
    *   **Content Area (Bottom)**: This area switches between:
        *   **Terminal View**: The default view. Use this to type commands (e.g., `/help`, `/init`, `/code <your task>`). It features command history (use Up/Down arrows).
        *   **Chat View**: Activates when you select or create a chat thread. Displays the conversation with the AI in message bubbles.

*   **Right Pane:**
    *   **Project File Tree**: Navigate your project's directory structure.
        *   Select files and use `+ Chat Ctx` / `- Chat Ctx` to add/remove them from the current chat's context.
        *   Use `+ Code Ctx` / `- Code Ctx` to stage/unstage files for `/code` operations.
        *   Files in chat context are highlighted (e.g., blue), code context (e.g., red), and indexed files (e.g., green).
        *   Refresh the tree with the `↺` button.
    *   **Model Selector**: Choose the AI model for general interactions. Models are grouped by provider. Selecting a model here updates the active model for the current session.

### Key UI Interactions & Workflows

*   **Starting a New Chat**:
    1.  Click `+ New Chat` in the Left Pane.
    2.  The Middle Pane will switch to the Chat View for the new thread.
    3.  Type your message in the "Chat Input" area at the bottom of the Chat View and press Enter.

*   **Chatting About Specific Files**:
    1.  In the Right Pane, navigate the File Tree to find the desired file(s).
    2.  Select a file.
    3.  Click `+ Chat Ctx`. The file is now part of the current chat's context.
    4.  In the Chat View, ask questions related to the file(s).

*   **Requesting Code Changes (`/code` command)**:
    1.  **Stage Context (Optional but Recommended)**: In the Right Pane's File Tree, select files relevant to your coding task and click `+ Code Ctx`. These files will provide crucial context to the AI.
    2.  **Initiate Command**: In the Terminal View (Middle Pane), type `/code <your detailed coding task description>`. For example: `/code add a new class UserProfile with fields name, email, and bio, and include a method to validate the email format`.
    3.  **AI Planning (Steps Screen)**: JrDev's AI will analyze your request and the provided context, then propose a series of steps to achieve the task. This plan is presented on a "Steps Screen". You can:
        *   `Continue`: Accept the proposed steps.
        *   `Save Edits`: Modify the steps (e.g., reorder, rephrase, add/remove) and then continue.
        *   `Re-Prompt`: Provide additional instructions or clarifications to the AI to regenerate the steps.
        *   `Auto Accept`: Proceed with current steps and automatically accept all subsequent confirmation prompts for this task (use with caution).
        *   `Cancel`: Abort the `/code` command.
    4.  **AI Implementation & Confirmation (Code Confirmation Screen)**: For each step (or a batch of changes), the AI will generate code. JrDev will then display a "Code Confirmation Screen" showing a diff of the proposed changes. You can:
        *   `Yes`: Apply the changes to your local files.
        *   `No`: Reject the changes for the current step/batch and potentially end or modify the task.
        *   `Edit`: (If available) Manually edit the proposed code before applying.
        *   `Request Change`: Send feedback to the AI to revise the current set of changes.
        *   `Auto Accept`: Apply current changes and automatically accept further changes in this task.
    5.  **Review & Validation**: After all steps are processed, the AI may perform a final review of all changes or validate the modified files to ensure correctness and adherence to the task.

*   **Changing AI Model**:
    *   For general use: Select a model from the Model Selector in the Right Pane.
    *   For specific tasks (profiles): Click "Profiles" in the Left Pane, select a profile (e.g., "code_generation"), click "Change Model", and choose a model for that profile.

*   **Managing Project Context for Chat**:
    *   In the Chat View, toggle the "Project Ctx" switch. When enabled, JrDev adds summarized information about your project (file tree, select file summaries generated by `/init`, project overview) to the chat context.

*   **Git PR Operations**:
    1.  Click "Git Tools" in the Left Pane.
    2.  Configure your "Base Branch" (e.g., `origin/main`) if needed and save.
    3.  Switch to "PR Summary" or "PR Review" tab.
    4.  Optionally add custom instructions.
    5.  Click "Generate Summary" or "Generate Review". The output will appear in the text area below.

### Common Commands (typed in Terminal View)

While many functions are accessible via UI elements, some core commands are still typed:

*   `/help`: Show the help message with all available commands.
*   `/init`: **Crucial for new projects.** Makes JrDev project-aware by scanning your codebase. It indexes key files, understands the file structure, infers coding conventions, and generates summary documents (e.g., `jrdev_overview.md`, `jrdev_conventions.md`). This rich, token-efficient context enables highly relevant AI assistance.
*   `/code <message>`: Initiates an AI-driven coding task. Provide a detailed description of the desired change or feature. JrDev will guide an AI through a multi-step process including planning, implementation (with your approval of diffs), and review. Uses files staged via `+ Code Ctx` in the File Tree as primary context.
*   `/model <model_name>`: (Alternative to Model Selector) Change the active model.
*   `/models`: List all available models.
*   `/cost`: Display session costs.
*   `/tasks`: List active background AI tasks.
*   `/cancel <task_id>|all`: Cancel specific or all background tasks.
*   `/thread <new|list|switch|info|view|rename|delete>`: Manage chat threads (largely covered by Chat List and Chat View controls).
*   `/addcontext <file_path or pattern>`: (Alternative to File Tree) Add file(s) to context.
*   `/viewcontext [number]`: View the LLM context window content for the current chat.
*   `/projectcontext <on|off|status|help>`: (Alternative to Chat View switch) Manage project-wide context.
*   `/clearcontext`: Clear context and conversation history for the current thread.
*   `/stateinfo`: Display terminal state information.
*   `/exit`: Exit JrDev.

## API Providers and Models

JrDev is designed to work with a variety of Large Language Model (LLM) providers. The list of available models is dynamically populated based on your configured API keys and the models defined in the application's configuration.

**Model Configuration:**
The primary list of supported models is managed in the `src/jrdev/model_list.json` file. This JSON file allows for easy addition, removal, or modification of model entries. Each entry typically specifies the model name, its provider, cost information, context window size, and whether it's designated as a "think" model (suitable for complex reasoning tasks).

**Supported API Providers:**
To use models from a specific provider, you'll need to configure the corresponding API key in JrDev (either via the TUI's "API Keys" screen or by setting environment variables in the `.env` file).

*   **Venice (`VENICE_API_KEY`)**:
    *   Provides access to a diverse range of open-source and proprietary models with a focus on privacy.
    *   Example models: `deepseek-r1-671b`, `qwen-2.5-coder-32b`, `llama-3.1-405b`.

*   **OpenAI (`OPENAI_API_KEY`)**:
    *   For using OpenAI's suite of models.
    *   Example models: `o4-mini-2025-04-16` (GPT-4o mini equivalent), `gpt-4.1-2025-04-14` (GPT-4.1 equivalent).

*   **Anthropic (`ANTHROPIC_API_KEY`)**:
    *   Access to Anthropic's Claude family of models.
    *   Example models: `claude-3-5-haiku-20241022`, `claude-3-7-sonnet-20250219`.

*   **DeepSeek (`DEEPSEEK_API_KEY`)**:
    *   For models from DeepSeek AI.
    *   Example models: `deepseek-reasoner`, `deepseek-chat`.

*   **OpenRouter (`OPEN_ROUTER_KEY`)**:
    *   Aggregates models from various sources, offering a unified API.
    *   Example models: `deepseek/deepseek-r1`, `google/gemini-2.5-pro-preview`, `meta-llama/llama-4-maverick`.

**Viewing Available Models:**
The most up-to-date list of models available to you (based on your configured keys and the `model_list.json` file) can always be found by:
*   Using the **Model Selector** in the Right Pane of the TUI.
*   Running the `/models` command in the Terminal View.

## Development

```bash
# Clone the repository
git clone https://github.com/presstab/jrdev.git
cd jrdev

# Install in development mode
pip install -e .
# Also ensure dev dependencies are installed (e.g., from requirements-dev.txt if available)
```

### Development Commands

```bash
# Run linting (example)
flake8 src/ tests/

# Run type checking (example)
mypy --strict src/

# Format code (example)
black src/ tests/

# Sort imports (example)
isort src/ tests/
```
(Please adapt these to your project's actual linting/formatting setup as defined in your contribution guidelines or dev tooling.)

## License

This project is licensed under the MIT License with Commons Clause - see the [LICENSE](LICENSE) file for details.