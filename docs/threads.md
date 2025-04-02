# Working with Message Threads in JrDev

JrDev supports multiple conversation threads, each with isolated context and message history. This feature is useful when working on different tasks or projects simultaneously.

## Command Reference

| Command | Description |
|---------|-------------|
| `/thread new [NAME]` | Create a new thread with optional name |
| `/thread list` | List all available threads |
| `/thread switch THREAD_ID` | Switch to a different thread |
| `/thread info` | Show information about the current thread |
| `/thread view [COUNT]` | View conversation (default: 10 messages) |

## Thread Concepts

- **Thread**: A self-contained conversation with its own message history and context files
- **Main Thread**: The default thread created when JrDev starts
- **Active Thread**: The thread you're currently interacting with
- **Thread ID**: A unique identifier for each thread (main or thread_XXXXXXXX)

## Thread Features

- **Isolated Conversations**: Each thread maintains its own separate message history
- **Context Isolation**: Context files are stored at the thread level
- **Visual Indicators**: The active thread is shown in the prompt
- **Thread Management**: Commands for creating, listing, switching between threads

## Thread Commands

### Creating a New Thread

Create a new thread with:

```
> /thread new
Created and switched to new thread: thread_a1b2c3d4
```

You can also provide a custom name:

```
> /thread new frontend_task
Created and switched to new thread: frontend_task
```

### Listing All Threads

List all available threads with:

```
> /thread list
Message Threads:
  main - 4 messages, 2 context files
* thread_a1b2c3d4 - 0 messages, 0 context files
  frontend_task - 2 messages, 3 context files
```

The active thread is marked with an asterisk (*).

### Switching Between Threads

Switch to a different thread with:

```
> /thread switch main
Switched to thread: main
```

### Viewing Thread Information

View detailed information about the current thread:

```
> /thread info
Thread ID: main
Total messages: 4
  User messages: 2
  Assistant messages: 2
  System messages: 0
Context files: 2
Files referenced: 3

Context files:
  /home/user/project/src/main.py
  /home/user/project/src/utils.py

💬 Thread: main
───────────────────────────────────────────
👤 You:
   explain how the main.py file works
   · · ·
🤖 Assistant:
   The main.py file serves as the entry point for the application. It initializes the core components...
```

### Viewing Conversation History

View the conversation history for the current thread:

```
> /thread view
💬 Thread: frontend_task
───────────────────────────────────────────
👤 You:
   how should I structure the React components?
   · · ·
🤖 Assistant:
   For your frontend application, I recommend structuring your React components using a feature-based approach...
```

By default, this shows the last 10 messages. You can specify a different number:

```
> /thread view 5
```

## Best Practices

- **Create Topic-Specific Threads**: Use separate threads for different areas of your project
- **Add Context**: Use `/addcontext` to add relevant files to the current thread
- **Task-Based Threads**: Create a new thread for each specific task you're working on
- **Switch When Context Changes**: When shifting focus to a different part of the project, switch to a different thread
- **Review History**: Use `/thread view` to quickly see previous conversations in a thread