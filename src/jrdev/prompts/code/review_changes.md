Review the provided files and user request. A summary of changes has been provided to you using diff format. These files have had new code implemented in an attempt to satisfy the user's request. Evaluate whether the implementation successfully meets the user's requirements.

Your response MUST be in the following JSON format:
```json
{
  "success": true|false,
  "reason": "Detailed explanation of why the implementation succeeds or fails to meet requirements",
  "action": "Specific action needed if implementation is insufficient, or 'none' if successful"
}
```

For the "success" field, use true if the user's request is fully met, false otherwise.
For the "reason" field, provide a clear, concise explanation of your evaluation.
For the "action" field:
- If success is true: use "none"
- If success is false: provide specific guidance on what needs to be fixed

Evaluate only the implementation against the user's requirements. Do not suggest improvements beyond what was requested.