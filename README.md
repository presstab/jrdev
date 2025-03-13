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

Create a `.env` file in your project root directory with your API key:

```
VENICE_API_KEY=your_api_key_here
```

## Usage

After installation, you can run the JrDev terminal from anywhere on your system:

```bash
jrdev
```

To specify a model:

```bash
jrdev --model llama-3.1-405b
```

For more options:

```bash
jrdev --help
```

### Available Commands

- `/exit` - Exit the terminal
- `/model <model_name>` - Change the model
- `/models` - List all available models
- `/clear` - Clear conversation history
- `/clearmessages` - Clear message history but keep context
- `/clearcontext` - Clear context but keep message history
- `/addcontext <file_path>` - Add a file to context
- `/viewcontext` - View current context
- `/code` - Enter code mode for code generation
- `/help` - Show the help message
- `/asyncsend` - Send a request asynchronously
- `/cancel` - Cancel an ongoing request
- `/cost` - Display token usage and cost information

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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.