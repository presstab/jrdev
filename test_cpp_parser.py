#!/usr/bin/env python3
import sys
sys.path.append('/home/pt/workspace/jrdev')
from src.jrdev.languages.cpp_lang import CppLang

# Create an instance of CppLang
cpp_lang = CppLang()

# Parse a header file
header_path = '/home/pt/workspace/jrdev/tests/mock/pricechartwidget.h'
header_functions = cpp_lang.parse_functions(header_path)

# Parse implementation file
impl_path = '/home/pt/workspace/jrdev/tests/mock/pricechartwidget.cpp'
impl_functions = cpp_lang.parse_functions(impl_path)

# Print all functions found in header file
print(f"Found {len(header_functions)} functions in header file:")
for func in header_functions:
    print(f"Class: {func['class']}, Name: {func['name']}, Lines: {func['start_line']}-{func['end_line']}")

print("\n" + "="*50 + "\n")

# Print all functions found in implementation file
print(f"Found {len(impl_functions)} functions in implementation file:")
for func in impl_functions:
    print(f"Class: {func['class']}, Name: {func['name']}, Lines: {func['start_line']}-{func['end_line']}")