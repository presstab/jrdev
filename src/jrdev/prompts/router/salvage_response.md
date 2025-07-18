**INSTRUCTIONS**: Parse the included message. It is a malformed response with JSON that failed to parse. Salvage this response by formatting it in the following format:
```json
{
  decision: "execute_action" | "clarify" | "chat" | "summary",
  reasoning: string,  // Always required - explain your decision
  
  // For execute_action only:
  action?: {
    type: "tool" | "command",
    name: string,
    args: string[]
  },
  final_action?: boolean,  // false for tools, true for commands
  
  // For clarify only:
  question?: string,
  
  // For chat/summary only:
  response?: string
}
```

**CRITICAL**
- Your response must begin with ```json and it must end with ```
- The must be no text or characters between ```json and the json object. Likewise, there must be no characters after the JSON object ends and the ```.
- There must be no comments included within the JSON object or anywhere else.
- You must not alter the text in anyway. You are only able to alter formatting.
- If a field in the object is missing, include the key and use a blank - parsable value. For example `"question": ""`.