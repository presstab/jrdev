import re

def parse_cpp_functions(file_path):
    # This regex attempts to capture an optional class name and the function name.
    # Group 1: class name (if present, e.g., "thisclass")
    # Group 2: function name (e.g., "func1")
    func_regex = re.compile(
        r'^\s*(?:[\w:&*<>\s]+)?(?:(\w+)::)?(\w+)\s*\([^)]*\)\s*\{'
    )

    with open(file_path, 'r') as f:
        lines = f.readlines()

    functions = []
    total_lines = len(lines)
    line_num = 0  # index starting at 0

    while line_num < total_lines:
        line = lines[line_num]
        match = func_regex.match(line)
        if match:
            class_name = match.group(1)  # Will be None if no class is specified
            function_name = match.group(2)
            start_line = line_num + 1  # converting to 1-indexed line number
            brace_count = line.count('{') - line.count('}')
            end_line = start_line

            # Continue scanning subsequent lines until braces are balanced
            while brace_count > 0 and line_num < total_lines - 1:
                line_num += 1
                current_line = lines[line_num]
                brace_count += current_line.count('{')
                brace_count -= current_line.count('}')
                end_line = line_num + 1

            new_func = {"class": class_name, "name":function_name, "start_line": start_line, "end_line": end_line}
            functions.append(new_func)
        line_num += 1

    return functions

def parse_cpp_signature(signature: str):
    # This regex captures the class name and function name.
    # It handles cases where the function name might be a destructor (starting with ~).
    pattern = re.compile(r'^\s*([a-zA-Z_]\w*)::(~?[a-zA-Z_]\w*)\s*\(')
    match = pattern.match(signature)
    if match:
        class_name = match.group(1)
        function_name = match.group(2)
        return class_name, function_name
    return None, None