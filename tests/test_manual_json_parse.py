#!/usr/bin/env python3
import sys
sys.path.append('/home/pt/workspace/jrdev')
from jrdev.file_operations.file_utils import manual_json_parse

# Test JSON with boolean values
test_json = """
{
  "changes": [
    {
      "operation": "ADD",
      "filename": "assetbox.h",
      "insert_location": {
        "global": true
      },
      "new_content": "#include <QMouseEvent>\\n",
      "sub_type": "BLOCK"
    },
    {
      "operation": "ADD",
      "filename": "assetbox.h",
      "insert_location": {
        "global": false
      },
      "new_content": "#include <QMouseEvent>\\n",
      "sub_type": "BLOCK"
    }
  ]
}
"""

# Parse the JSON
result = manual_json_parse(test_json)
print("Parsed result:")
import pprint
pprint.pprint(result)