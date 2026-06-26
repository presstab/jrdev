**INSTRUCTIONS**: Parse the included message. It is a malformed response with JSON that failed to parse. Salvage this response by returning a valid JSON object with these fields:

- `decision`: one of `execute_action`, `clarify`, `chat`, or `summary`
- `reasoning`: always required
- `action`: required only for `execute_action`, with `type`, `name`, and `args`
- `final_command`: required only for `execute_action`; false for tools, true for commands
- `question`: required only for `clarify`
- `response`: required only for `chat` and `summary`

Example:
```json
{
  "decision": "execute_action",
  "reasoning": "The request requires a command.",
  "action": {
    "type": "command",
    "name": "command_or_tool_name",
    "args": []
  },
  "final_command": true
}
```

**CRITICAL RULES**
- Your response must begin with ```json and end with ```
- There must be no text or characters between ```json and the JSON object, or after the JSON object ends and before ```
- There must be no comments included within the JSON object or anywhere else
- You must not alter the semantic meaning of the content - only fix formatting issues
- Common failure patterns to fix:
  - Missing closing quotes on string fields, especially `response`
  - Missing closing backticks in code blocks within strings
  - Missing closing braces for the JSON object
  - Unescaped backslashes in strings, such as `\n` when it should be `\\n`
  - Missing commas between fields
- If a field is missing, include the key with a blank parsable value, such as `"question": ""`
- Preserve all original content exactly as written, only fixing structural JSON issues
- Special attention: When the `response` field contains markdown or code blocks, ensure:
  - All backticks are properly closed
  - The entire markdown content is properly quoted
  - No unescaped special characters break the JSON string
