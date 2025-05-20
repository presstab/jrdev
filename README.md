# JrDev Terminal

A command-line interface for interacting with JrDev's LLM models using OpenAI-compatible APIs.

## Requirements

- Python 3.7 or higher
- Venice API key (or other OpenAI-compatible API)

## Installation

```bash
# Install from the current directory
pip install -e .

# Or install directly from GitHub
pip install git+https://github.com/presstab/jrdev.git

# Alternatively, install using requirements.txt
pip install -r requirements.txt
```

## Configuration

### API Keys

JrDev requires at least one API key to function. Create a `.env` file in your project root directory with your API keys:

1. **Venice API Key** (required for Venice models): Get your API key from [Venice](https://venice.ai)
2. **OpenAI API Key** (optional, only needed for OpenAI models): Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)

Example `.env` file:

```
VENICE_API_KEY=your_venice_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional, needed for OpenAI models
```

For convenience, an example file `.env_example` is included in the repository that you can copy and edit:

```bash
cp .env_example .env
# Then edit .env to add your actual API keys
```

## Usage

After installation, you can run the JrDev terminal from anywhere on your system:

```
$ jrdev
```

When using JrDev in a project directory, you should first run the `/init` command to familiarize the AI with your project:

```
$ jrdev
> /init
```

This will scan and index important files in your project, helping the AI understand your codebase structure and context.

To see available models:

```
$ jrdev
> /models
```

To specify a model:

```
$ jrdev
> /model llama-3.1-405b
```

For help with available commands:

```
$ jrdev
> /help
```

You can directly ask questions without any command (defaults to `/chat`):

```
$ jrdev
> is this code production ready?
deepseek-r1-671b is processing request...
Receiving response from deepseek-r1-671b...

The application demonstrates a solid architectural foundation but...
```

### Available Commands

#### Basic
- `/exit` - Exit the terminal
- `/help` - Show the help message
- `/cost` - Display session costs

#### Use AI
- `/model <model_name>` - Change model
- `/models` - List all available models
- `/init` - Index important project files and familiarize LLM with project
- `/code <message>` - Send coding task to LLM. LLM will read and edit the code
- `/asyncsend [filepath] <prompt>` - Send message in background and save to a file
- `/chat <message>` - Chat with the AI about your project (default)
- `/tasks` - List active background tasks
- `/cancel <task_id>|all` - Cancel background tasks

#### Thread & Context Control
- `/thread <new|list|switch|info|view>` - Manage separate message threads with isolated context
- `/addcontext <file_path or pattern>` - Add file(s) to the LLM context window
- `/viewcontext [number]` - View the LLM context window content
- `/projectcontext <argument|help>` - Manage project context for efficient LLM interactions
- `/clearcontext` - Clear context and conversation history
- `/clearmessages` - Clear message history for all models
- `/stateinfo` - Display terminal state information

### Available Models

#### Venice Models
- `deepseek-r1-671b` - High capacity model with 131k context
- `qwen-2.5-coder-32b` - Specialized coding model
- `qwen-2.5-qwq-32b` - Advanced thinking model
- `llama-3.3-70b` - Large Llama 3.3 model
- `llama-3.1-405b` - Largest Llama model
- `llama-3.2-3b` - Smaller Llama model with 131k context
- `dolphin-2.9.2-qwen2-72b` - Dolphin model with 32k context
- `mistral-31-24b` - Large Mistral model with 131k context

#### OpenAI Models (requires OPENAI_API_KEY)
- `o3-mini-2025-01-31` - OpenAI o3 mini model
- `gpt-4o` - Latest OpenAI GPT-4o model
- `gpt-4-turbo` - Faster GPT-4 model
- `gpt-3.5-turbo` - Affordable GPT-3.5 model

### Using Message Threads

JrDev supports multiple conversation threads with isolated contexts, similar to chat applications. Each thread maintains its own conversation history and context files.

Create a new thread:
```
$ jrdev
> /thread new
Created and switched to new thread: thread_a1b2c3d4
```

List available threads:
```
> /thread list
Message Threads:
  main - 0 messages, 0 context files
* thread_a1b2c3d4 - 0 messages, 0 context files
```

Switch between threads:
```
> /thread switch main
Switched to thread: main
```

View thread information:
```
> /thread info
Thread ID: main
Total messages: 4
  User messages: 2
  Assistant messages: 2
  System messages: 0
Context files: 2
Files referenced: 3
```

View conversation history:
```
> /thread view
```

## Development

```bash
# Clone the repository
git clone https://github.com/presstab/jrdev.git
cd jrdev

# Install in development mode
pip install -e .
```

### Development Commands

```bash
# Run linting
flake8 src/

# Run type checking
mypy --strict src/

# Format code
black src/

# Sort imports
isort src/
```

## License

This project is licensed under the MIT License with Commons Clause - see the [LICENSE](LICENSE) file for details.