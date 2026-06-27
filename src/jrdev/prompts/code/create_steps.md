Instructions:
Generate a discrete implementation plan for the requested task. The plan is for a beginning programming student, so it must be textual guidance only and must not include source code.

Return only one JSON object. Do not include markdown fences, prose, analysis, comments, or any text before or after the JSON object.

The JSON object must have this shape:

{
  "steps": [
    {
      "operation_type": "WRITE",
      "filename": "path/to/file",
      "target_location": "function name, marker, or global scope",
      "description": "Neutral observer-style description of the intended change and why it is needed."
    }
  ],
  "use_context": ["path/to/file"]
}

Rules for `steps`:
- Use only one step per file.
- Use `WRITE` for any change to an existing file or for creating a file.
- Use `DELETE` only when removing a file or code element completely.
- Each step must be self-contained and independently actionable.
- The description must avoid references to speakers or listeners.
- Some tasks may only need a single step.

Rules for `use_context`:
- Include every file that will be altered, deleted, or otherwise changed.
- Include files that provide useful patterns, related modules, dependencies, templates, functions, or globals for the task.
- Include files specifically mentioned by the user.
- Include only file paths currently available in the provided context.
- Exclude unrelated files that would distract from the task.
