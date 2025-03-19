#!/usr/bin/env python3
import sys
sys.path.append('/home/pt/workspace/jrdev')
from src.jrdev.languages.cpp_lang import CppLang

# Create an instance of CppLang
cpp_lang = CppLang()

# Parse a header file
header_path = '/home/pt/workspace/jrdev/tests/mock/pricechartwidget.h'
functions = cpp_lang.parse_functions(header_path)

# Print all functions found
print(f"Found {len(functions)} functions in {header_path}:")
for func in functions:
    print(f"Class: {func['class']}, Name: {func['name']}, Lines: {func['start_line']}-{func['end_line']}")