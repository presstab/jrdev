# JrDev Terminal - AI-Powered Developer Assistant
![code-fast](https://github.com/user-attachments/assets/5efa7671-c2bd-4343-8338-bb2d482cb02f)

JrDev is a powerful, AI-driven assistant designed to integrate seamlessly into your development workflow. It offers a rich Textual User Interface (TUI) for interacting with various Large Language Models (LLMs) like those from OpenAI, Anthropic, and Venice. Streamline your coding, review, and project understanding tasks directly from your terminal.

```bash
pip install jrdev
```

JrDev is free and open source. All of your data is routed directly through your API provider.

While a basic command-line interface (`jrdev-cli`) is available, the primary and recommended way to use JrDev is through its interactive TUI, launched with the `jrdev` command.

![jrdev-cli-tui](https://github.com/user-attachments/assets/609defda-521c-4ada-a9d8-d0c0efa56381)

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


https://github.com/user-attachments/assets/8eb586ad-138b-400e-a9fa-aa30876f5252


*   **Versatile Model Management**:
    *   Easily select from a list of available LLMs from different providers.
    *   Configure Model Profiles to assign specific models to different tasks (e.g. one model for task planning, another for complex code generation, and a different model for file indexing).
*   **Real-time Task Monitoring**: Keep an eye on ongoing AI operations, including token usage and status, with the ability to cancel tasks.
*   **Intuitive File Navigation**: Browse your project's file tree, and easily add files to the AI's context for chat or code operations.


https://github.com/user-attachments/assets/127f26d0-c4f6-4f43-8609-0685a1db1ab6


*   **Centralized Configuration**: Manage API keys and model profiles through dedicated TUI screens.
*   **Persistent History**: Command history in the terminal input and chat history within threads are saved.

## 🚨Early Access Software🚨

JrDev is in early development and may undergo rapid changes, including breaking changes and experimental features. This tool can modify your project files, and will prompt for confirmation unless placed in "Accept All" mode. **It is strongly recommended to use version control (e.g., Git) and commit your work before using JrDev.**

## Requirements

*   Python 3.7 or higher
*   API Keys for one or more LLM providers.

## Installation

Install JrDev directly from the Python Package Index (PyPI):
```bash
pip install jrdev
```

For developers or to get the very latest updates, you can install from the GitHub repository:
```bash
# Install from a cloned repository in editable mode
pip install -e .

# Or install the latest version directly from GitHub
pip install git+https://github.com/presstab/jrdev.git
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

The JrDev TUI is a comprehensive dashboard for your AI development tasks. The main components are:

*   **Main Content Area**: This central part of the screen switches between the **Terminal View** and the **Chat View**.
    *   **Terminal View**: Your command center. Type commands like `/help`, `/init`, and `/code` here.
    *   **Chat View**: Activates when you start or select a chat. This is where you have conversations with the AI.
*   **Sidebar Panels**:
    *   **Chat List & Settings**: On the left, you can manage your chat threads (start new ones, switch between them) and access settings for API Keys, Model Profiles, and Git Tools.
    *   **Project Files & Model Selector**: On the right, you can browse your project's file tree to add files to the AI's context. Below the file tree, you can select the active AI model for your session.
*   **Task Monitor**: Located above the main content area, this panel shows the status of all ongoing and completed AI tasks, letting you monitor progress and token usage.

### Key UI Interactions & Workflows

*   **Starting a New Chat**:
    1.  Click `+ New Chat` in the left sidebar.
    2.  The main area will switch to the Chat View for the new thread.
    3.  Type your message in the "Chat Input" area at the bottom and press Enter.

*   **Chatting About Specific Files**:
    1.  In the right sidebar, navigate the File Tree to find the desired file(s).
    2.  Select a file and click `+ Chat Ctx` to add it to the current chat's context.
    3.  In the Chat View, ask questions related to the file(s).

*   **Requesting Code Changes (`/code` command)**:
    1.  **Stage Context (Optional but Recommended)**: In the right sidebar's File Tree, select files relevant to your coding task and click `+ Code Ctx`. These files will provide crucial context to the AI.
    2.  **Initiate Command**: In the Terminal View, type `/code <your detailed coding task description>`. For example: `/code add a new class UserProfile with fields name, email, and bio, and include a method to validate the email format`.
    3.  **AI Planning (Steps Screen)**: JrDev's AI will analyze your request and propose a series of steps. You can review, edit, or accept this plan.
    4.  **AI Implementation & Confirmation (Code Confirmation Screen)**: For each step, the AI generates code. JrDev displays a diff of the proposed changes for you to approve, reject, or request revisions.
    5.  **Review & Validation**: After all steps are processed, the AI may perform a final review of all changes to ensure correctness.

*   **Changing AI Model**:
    *   For general use: Select a model from the Model Selector in the right sidebar.
    *   For specific tasks (profiles): Click "Profiles" in the left sidebar to assign different models to tasks like "code_generation" or "chat".

*   **Managing Project Context for Chat**:
    *   In the Chat View, toggle the "Project Ctx" switch. When enabled, JrDev adds summarized information about your project (from `/init`) to the chat context.

*   **Git PR Operations**:
    1.  Click "Git Tools" in the left sidebar.
    2.  Configure your "Base Branch" (e.g., `origin/main`) if needed.
    3.  Generate a PR summary or review from the respective tabs.

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

JrDev supports multiple Large Language Model (LLM) providers. To use models from a provider, you must add the corresponding API key in the TUI (`Settings -> API Keys`).

**Built-in Provider Support:**
*   **Venice (`VENICE_API_KEY`)**
*   **OpenAI (`OPENAI_API_KEY`)**
*   **Anthropic (`ANTHROPIC_API_KEY`)**
*   **DeepSeek (`DEEPSEEK_API_KEY`)**
*   **OpenRouter (`OPEN_ROUTER_KEY`)**
*   **Ollama** (for local models)

The list of available models is populated dynamically based on your configured API keys. You can see the full list in the **Model Selector** panel in the TUI or by running the `/models` command.

**Adding Custom Providers:**
JrDev is extensible. You can add support for other OpenAI-compatible API providers directly through the TUI using the `/provider add` command.

## Development

```bash
# Clone the repository
git clone https://github.com/presstab/jrdev.git
cd jrdev

# Install in development mode
pip install -e .
# Also ensure dev dependencies are installed
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

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
