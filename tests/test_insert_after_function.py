#!/usr/bin/env python3
import sys
import os
sys.path.append('/home/pt/workspace/jrdev')
from jrdev.file_operations.file_utils import insert_after_function

# Create a test file with a simple C++ function
test_cpp_content = """
class TestClass {
public:
    void testFunction() {
        // Function content
    }
};
"""

# Create a test file
test_file_path = "test_function.cpp"
with open(test_file_path, "w") as f:
    f.write(test_cpp_content)

print("Created test file with content:")
print(test_cpp_content)

# Case 1: Test with content that doesn't have a newline at the end
print("\nTest 1: Adding content without a newline")
change = {
    "insert_after_function": "testFunction",  # Just using function name since class detection isn't working in this simplified test
    "new_content": "// New content without newline"
}

with open(test_file_path, "r") as f:
    lines = f.readlines()

insert_after_function(change, lines, test_file_path)

with open(test_file_path, "w") as f:
    f.writelines(lines)

with open(test_file_path, "r") as f:
    result = f.read()

print("Result:")
print(result)

# Clean up
os.remove(test_file_path)
print("\nTest file removed")