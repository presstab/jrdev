# JrDev Terminal

A command-line interface for interacting with JrDev's LLM models using OpenAI-compatible APIs.

## Installation

```bash
# Install from the current directory
pip3 install -e .

# Or install directly from GitHub
pip3 install git+https://github.com/presstab/jrdev.git
```

## Usage

After installation, you can run the JrDev terminal from anywhere on your system:

```bash
jrdev
```

### Available Commands

- `/exit` - Exit the terminal
- `/model <model_name>` - Change the model
- `/models` - List all available models
- `/clear` - Clear conversation history
- `/help` - Show the help message

### Available Models

- deepseek-r1-671b
- deepseek-r1-llama-70b
- qwen-2.5-coder-32b
- llama-3.1-405b
- llama-3.2-3b
- llama-3.3-70b

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/jrdev.git
cd jrdev

# Install in development mode
pip3 install -e .
```