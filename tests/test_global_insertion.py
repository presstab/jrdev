#!/usr/bin/env python3
import sys
sys.path.append('/home/pt/workspace/jrdev')
from jrdev.file_operations.file_utils import manual_json_parse, apply_file_changes
import os
import tempfile

# Test JSON with boolean values
test_json = """
{
  "changes": [
    {
      "operation": "ADD",
      "filename": "testfile.h",
      "insert_location": {
        "global": true
      },
      "new_content": "#include <QMouseEvent>\\n",
      "sub_type": "BLOCK"
    }
  ]
}
"""

# Create a temporary file for testing
with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.h', dir='.') as f:
    f.write("// existing content\n")
    temp_filepath = f.name

print(f"Created temporary file: {temp_filepath}")

# Rename to match the filename in the JSON
os.rename(temp_filepath, "testfile.h")
print("Renamed to: testfile.h")

# Parse the JSON and apply changes
parsed_json = manual_json_parse(test_json)
print("Parsed JSON:")
import pprint
pprint.pprint(parsed_json)

# Apply changes
print("\nApplying changes...")
apply_file_changes(parsed_json)

# Print the file content after changes
print("\nContent after changes:")
with open("testfile.h", 'r') as f:
    print(f.read())

# Clean up the test file
os.remove("testfile.h")
print("Removed test file")