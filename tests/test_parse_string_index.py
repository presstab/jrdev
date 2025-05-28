#!/usr/bin/env python3
import sys
sys.path.append('/home/pt/workspace/jrdev')
from jrdev.file_operations.file_utils import manual_json_parse

# Load the test file
test_file_path = '/home/pt/workspace/jrdev/tests/mock/string_index_out_of_range.txt'

with open(test_file_path, 'r') as f:
    file_content = f.read()

print("File content:")
print(file_content)

# Try to parse the JSON content
print("\nAttempting to parse with manual_json_parse...")
try:
    result = manual_json_parse(file_content)
    print("\nParsed result:")
    import pprint
    pprint.pprint(result)
    
    # Verify the parsed content
    if 'changes' in result and len(result['changes']) > 0:
        change = result['changes'][0]
        
        # Check each expected field
        print("\nVerifying fields:")
        print(f"Operation: {change.get('operation')} (expected: ADD)")
        print(f"Filename: {change.get('filename')} (expected: pricechartwidget.cpp)")
        print(f"Insert location has after_function: {'after_function' in change.get('insert_location', {})} (expected: True)")
        print(f"After function value: {change.get('insert_location', {}).get('after_function')} (expected: UpdateAssetBoxes)")
        print(f"Sub type: {change.get('sub_type')} (expected: FUNCTION)")
        
        # Check if the new_content contains expected text
        new_content = change.get('new_content', '')
        expected_fragments = [
            "void PriceChartWidget::HandleAssetBoxClick",
            "AssetBox*",
            "m_mapAssetBoxes.remove"
        ]
        
        for fragment in expected_fragments:
            print(f"Contains '{fragment}': {fragment in new_content} (expected: True)")
    else:
        print("ERROR: No changes found in the parsed result")
except Exception as e:
    print(f"ERROR: Parsing failed with exception: {str(e)}")
    
    # Try to identify the issue
    import json
    try:
        # Try with standard json parser for comparison
        # Remove markdown code block markers
        clean_content = file_content.replace('```json', '').replace('```', '')
        json_result = json.loads(clean_content)
        print("\nStandard JSON parser succeeded. Issue might be in manual_json_parse implementation.")
    except json.JSONDecodeError as je:
        print(f"\nJSON parsing also failed: {str(je)}")
    except Exception as je:
        print(f"\nUnexpected error with JSON parsing: {str(je)}")