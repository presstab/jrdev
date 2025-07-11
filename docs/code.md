# Code Agent Overview

JrDev's `/code` command uses a structured coding agent to handle code generation tasks safely, effectively, and with careful consideration of costs. 

## Initiating a Code Task
A coding task is launched through the `Command Input` field in the JrDev Terminal screen. For the most precise and token-efficient way to start a code task invoke the `/code` command directly using the input field and pressing enter:  
```
>/code change the color of the text in the help display to cyan

Starting phase: Analyze Task

google/gemini-2.5-pro is processing the request... (advanced_reasoning profile)  
``` 
  
A code task can also be launched through the natural language intent router. This is done by typing the request into the same `Command Input` field without using the `/code` command. This essentially does the same thing, but adds an additional call to the AI model.
```  
>change the color of the text in the help display to cyan

Interpreting your request...

Running command: /code change the color of the text in the help display to cyan
Command Purpose: The user wants to change the color of text in the help display. This is a code modification task that requires the `/code` command.

Starting phase: Analyze Task

google/gemini-2.5-pro is processing the request... (advanced_reasoning profile)  
```  
 
### What About Context?

JrDev collected some essential context about the project during the `/init` phase. This is passed on to the coding agent. The coding agent goes through up to 3 rounds of searching to find the right files and context to include.

To manually add your own context to a coding task, use the 'Project Files' window and click '+ Code Ctx' on a file or directory to add it to the code context for the next code task. When a code task is launched, it clears any staged code context.

## Task Execution
The agent breaks down the requested task into distinct phases, that ensure context-aware planning, execution, and validation. This is a unique way to run an agent, many other products let the AI agent run wild and call whatever tools it wants throughout the process, which can lead to extensive token burn and bad results. JrDev's pipeline pattern gives the agent structure which allows for smart model switching that saves on costs, but delivers good results.

### Execution Phases:

```
User Request (/code "Add a new feature...")
    │
    ▼
┌────────────────────┐
│ 1. Analyze         │  ← Interpret task and identify needed files
└────────────────────┘
    │
    ▼
┌────────────────────┐
│ 2. Fetch Context   │  ← Gather file contents and project details
└────────────────────┘
    │
    ▼
┌────────────────────┐
│ 3. Plan            │  ← Generate step-by-step plan (user-reviewable)
└────────────────────┘
    │
    ▼
┌────────────────────┐
│ 4. Execute         │  ← Apply changes with diffs and confirmations
└────────────────────┘
    │
    ▼
┌────────────────────┐
│ 5. Review          │  ← Check if changes meet the original request
└────────────────────┘
    │
    ▼
┌────────────────────┐
│ 6. Validate        │  ← Ensure code is well-formed and error-free
└────────────────────┘
    │
    ▼
Completed Task (Files updated on disk)
```

## Analyze Phase:
**Purpose**: Analyze the task, produce basic plan, create initial list of files that are needed to execute the plan. 
**Model Profiles Used**: `Advanced Reasoning`  
**Prompts Used**: `code/analyze_task_return_getfiles`  
**Loaded Context**:
- User Supplied Context: Context added using the '+ Code Ctx' button  
- Project Summary Context: Project summary (from `/init`), Conventions (from /init), File Summaries (from `/init` as well as `/projectcontext`), current file tree  

**Result**: The `Advanced Reasoning` profile returns a brief summary of the task and a list of additional files that should be loaded into context to complete the task.

The advanced reasoning model examines your request against project context (e.g., file tree, conventions) to determine required files.
- **Fetch Context**: Pulls in relevant file contents and any user-added snippets for accurate processing.
- **Plan**: Creates a JSON plan of steps (e.g., ADD, MODIFY, DELETE), which you can review, edit, or approve.
- **Execute**: Implements each step, showing diffs for confirmation before writing to files.
- **Review**: Verifies the changes align with your intent; auto-reprompts if needed.
- **Validate**: Final syntax and format check to catch any issues.

## Fetch Context Phase:  
**Purpose**: Collect all files that are necessary to successfully complete the task  
**Model Profiles Used**: `Quick Reasoning`, `Low Cost Search`  
**Prompts Used**:  `get_files_format`, `files/salvage_files`, `get_files_check`  
**Loaded Context**:  
- Files requested in the Analyze Phase  
- User-supplied context files (added via the “+ Code Ctx” button)  

**Result**:  
1. The `Quick Reasoning` profile is invoked to “salvage” any malformed file-request responses. Sometimes the AI model from the previous phase doesn't return the exact JSON format expected, instead of scrapping the entire task it can usually be salvaged.  
2. User context is merged into the file list, ensuring manually added files aren’t lost.  
3. The `Low Cost Search` profile is used to perform an additional analysis of the current context and request additional files be loaded if needed.

## Plan Phase:  
**Purpose**: Split coding task into distinct steps  
**Model Profiles Used**: `Advanced Reasoning`  
**Prompts Used**: `code/create_steps`  
**Loaded Context**:  
- **Task Description**: User task 
- **File Contents**: All files gathered in the previous two phases
**Removed Context**:  
- Project Summary Context: Additional project metadata isn’t re-sent in this phase, to save tokens and keep the model focused only on the files and task at hand.  

**Result**:  
1. Bundles the task and each file’s content into a single LLM request under the `Advanced Reasoning` profile.  
2. Receives a “plan” (an ordered list of file modification steps). The plan is requested to be split into steps where each step relates to all operations done to a specific file.  
3. Parses and validates the JSON, ensuring every `filename` in the plan matches one of the loaded files.  
4. Opens an interactive UI prompt where the user can:  
   - **Accept** the plan as‐is  
   - **Edit** the plan manually  
   - **Accept All** (silence future confirmations)  
   - **Reprompt** the LLM with custom feedback. A re-prompt sends the pipeline back to the Analyze Phase. 
   - **Cancel** the entire code task  
5. On acceptance, sends final plan to the Execute Phase.

## Execute Phase:  
**Purpose**: Generate code and apply to files.  
**Model Profiles Used**: `Advanced Coding`  
**Prompts Used**: `code/implement_step`, `code/operations/write`  
**Loaded Context**:  
- **Plan Step**: One step sent at a time, don't add other steps as often times it will cause the AI model to do too much.   
- **File Contents**: All context files are sent in each step. The current/freshly edited files are sent not the pre-task files.  
- **Retry Feedback**: Optional `additional_prompt` when a previous apply requested changes  

**Result**:  
1. Iterates each step, updating the UI with `print_steps`.  
2. **DELETE** steps invoke `delete_with_confirmation`, deleting the file on “yes” or recording a user-cancelled marker.  
3. **WRITE** steps:  
   - Gather the latest file contents.  
   - Build a prompt combining the `implement_step` template and the operation-specific instructions.  
   - Send to the LLM under the `Advanced Coding` profile.  
   - Parse the returned JSON diff.  
   - Apply changes via `apply_file_changes`, which:  
     • Shows a diff and prompts the user (Accept, Accept All, Edit, No, Request Change).  
     • Honors “Accept All” for batch writes.  
     • On “request_change,” retries the step with the user’s feedback.  
4. Collects a second pass over any steps that failed initially.  

## Review Phase: 
**Purpose**: Ensure that all aspects of the task have been completed properly.  
**Model Profiles Used**: `Advanced Reasoning`  
**Prompts Used**: `review_changes`  

**Loaded Context**:  
- **Diffs of All Changes**:  
  • Unified diffs for each file added, modified, or deleted  
  • Special annotations for any user-cancelled DELETE steps  
- **Original User Request**  
- **Current File Contents**: The up-to-date text of every file in the original context plus any new or modified files  

**Result**:  
1. Assembles a review payload combining the diffs, the user’s original prompt, and the latest file contents.  
2. Sends this to the LLM under the `Advanced Reasoning` profile using the `review_changes` prompt.  
3. If the review determines the changes are insufficient, the pipeline goes back to the Analyze Phase with the failed review. This creates an *Agentic Loop* structure. 
4. If review passes, it is sent to the Validation Phase.

## Validate Phase:
**Purpose**: Cheap, quick, structural check of files from an alternative AI model. Solely displays a message, has no impact on the agentic loop.  
**Model Profiles Used**: `Intermediate Reasoning`  
**Prompts Used**: `validator`  

**Loaded Context**:  
- Current contents of every file that has been changed  

**Result**:  
1. Reads all modified files from disk and concatenates their contents.  
2. Invokes the LLM with the `validator` system prompt under the `Intermediate Reasoning` profile.  
3. LLM returns a single‐line verdict:  
   - `VALID` if every file is syntactically and structurally correct  
   - `INVALID: [filename][reason], …` if any file has errors  
4. On `VALID`, the UI displays “✓ Files validated successfully.”  
5. On `INVALID`, the UI extracts and shows “⚠ Files may be malformed: <reason>.”  
6. If the response is unrecognized, the UI warns “Could not determine file validation status.”

## Conclusion:
This pipeline creates a cost effective, structured agentic loop that minimizes errors, supports complex tasks, and lets the user be as involved in the pipeline as they see fit.
