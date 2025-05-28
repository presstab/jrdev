#!/usr/bin/env python3
import sys
import os
sys.path.append('/home/pt/workspace/jrdev')
from jrdev.file_operations.file_utils import insert_within_function
import logging
from jrdev.logger import setup_logger

# Setup logger
setup_logger()
logger = logging.getLogger("jrdev")

# Create a test file with a simple C++ function
test_cpp_content = """
class TestClass {
public:
    void testFunction() {
        int x = 10;
        // Special marker line
        if (x > 5) {
            x = 5;
        }
        return;
    }
};
"""

# Create a test file
test_file_path = "test_function.cpp"
with open(test_file_path, "w") as f:
    f.write(test_cpp_content)

print("Created test file with content:")
print(test_cpp_content)

# Mock the get_language_for_file function and other dependencies
class MockLangHandler:
    def __init__(self):
        self.language_name = "cpp"
    
    def parse_signature(self, signature):
        return None, "testFunction"
    
    def parse_functions(self, file_path):
        return [{
            "class": None,
            "name": "testFunction",
            "start_line": 4,  # 1-indexed
            "end_line": 10   # 1-indexed
        }]

# Mock the imported module
sys.modules['jrdev.languages'] = type('obj', (object,), {
    'get_language_for_file': lambda x: MockLangHandler()
})

# Helper function to apply a change and show results
def apply_change_and_show_result(change_name, change):
    print(f"\n{change_name}:")
    
    with open(test_file_path, "r") as f:
        lines = f.readlines()
    
    try:
        insert_within_function(change, lines, test_file_path)
        
        with open(test_file_path, "w") as f:
            f.writelines(lines)
        
        with open(test_file_path, "r") as f:
            result = f.read()
        
        print("Result:")
        print(result)
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

# Test 1: Insert after string match
print("\nTest 1: Insert after string match")
change1 = {
    "insert_location": {
        "within_function": "testFunction",
        "position_marker": {
            "after_line": "Special marker line"
        }
    },
    "new_content": "        // New content after marker\n"
}
success1 = apply_change_and_show_result("Insert after string match", change1)

# Test 2: Insert after line number
print("\nTest 2: Insert after line number")
change2 = {
    "insert_location": {
        "within_function": "testFunction",
        "position_marker": {
            "after_line": 2  # 0-indexed relative to function start (should be the "int x = 10;" line)
        }
    },
    "new_content": "        // New content after line number\n"
}
success2 = apply_change_and_show_result("Insert after line number", change2)

# Test 3: Test with non-existent string
print("\nTest 3: Test with non-existent string")
change3 = {
    "insert_location": {
        "within_function": "testFunction",
        "position_marker": {
            "after_line": "This line doesn't exist"
        }
    },
    "new_content": "        // This should not be inserted\n"
}
success3 = apply_change_and_show_result("Insert after non-existent string", change3)

# Test 4: Test with out-of-bounds line number
print("\nTest 4: Test with out-of-bounds line number")
change4 = {
    "insert_location": {
        "within_function": "testFunction",
        "position_marker": {
            "after_line": 20  # Way beyond the function length
        }
    },
    "new_content": "        // This should not be inserted\n"
}
success4 = apply_change_and_show_result("Insert after out-of-bounds line", change4)

# Clean up
os.remove(test_file_path)
print("\nTest file removed")

# Print summary
print("\nSummary:")
print(f"Test 1 (string match): {'Passed' if success1 else 'Failed'}")
print(f"Test 2 (line number): {'Passed' if success2 else 'Failed'}")
print(f"Test 3 (non-existent string): {'Passed' if not success3 else 'Failed'}")
print(f"Test 4 (out-of-bounds line): {'Passed' if not success4 else 'Failed'}")