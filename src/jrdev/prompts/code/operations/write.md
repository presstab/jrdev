WRITE: Write content to a file.
   - "operation": "WRITE"
   - "filename": the path of the file being written.
   - "new_content": the **entire** content of the file. If the file previously existing, this must contain ALL of the code in the file, including existing code and new modifications.
   - "cancel_step": (optional) Occasionally you will be asked to do a task that is already completed. If the task is finished, include the cancel_step key and an explanation as the value. Do not return other keys.