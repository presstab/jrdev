REPLACE: Replace an existing code block with new content.
   - "operation": "REPLACE"
   - "filename": the file to modify.
   - "target_type": the type of code to be replaced. Options include:
       - "FUNCTION": the entire function implementation.
       - "BLOCK": a specific block of code within a function.
       - "SIGNATURE": the function's declaration (parameters, return type, etc.).
       - "COMMENT": inline documentation or comment section.
   - "target_reference": an object that specifies the location of the code to be replaced.
        - function_name - name of the function
        - code_snippet (optional) - exact string match that should be removed.
   - "new_content": the replacement code.