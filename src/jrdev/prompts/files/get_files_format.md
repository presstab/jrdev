Respond only with a list of files in the format get_files ['path/to/file.cpp', 'path/to/file2.json', ...] etc. 
Do not include any other text or communication. You are currently in the directory marked ROOT, so do not include that 
in the path, as it will not properly reference the file. If you do not include "get_files" before the list, it we be invalid.
Example Files Request 1: 
`get_files ['src/main.py', 'tests/strings/string_test.py']`
Example Files Request 2: 
`get_files ['src/main.cpp', 'src/main.h', 'src/problems.h']`