import re

def parse_cpp_functions(file_path):
    # Improved regex that handles:
    # 1. Optional return type (potentially with spaces, templates, etc.)
    # 2. Class name with :: scope operator
    # 3. Function name (including destructors with ~)
    # 4. Parameters between parentheses
    # 5. Function might span multiple lines before opening brace
    
    # First pattern to detect start of function definition (with or without class scope)
    func_start_regex = re.compile(
        r'^\s*(?:[\w:&*<>\s]+\s+)?(?:(\w+)::)?(~?\w+)\s*\([^{;]*$'
    )
    
    # Pattern for function declarations that are all on one line
    inline_func_regex = re.compile(
        r'^\s*(?:[\w:&*<>\s]+\s+)?(?:(\w+)::)?(~?\w+)\s*\([^{;]*\)\s*(?:const|override|final|noexcept|=\s*default|=\s*delete|\s)*\s*\{'
    )

    with open(file_path, 'r') as f:
        lines = f.readlines()

    functions = []
    total_lines = len(lines)
    line_num = 0  # index starting at 0

    while line_num < total_lines:
        line = lines[line_num]
        
        # Try to match inline function definition first
        match = inline_func_regex.match(line)
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

            new_func = {"class": class_name, "name": function_name, "start_line": start_line, "end_line": end_line}
            functions.append(new_func)
        
        # Try to match multi-line function definition
        else:
            match = func_start_regex.match(line)
            if match:
                class_name = match.group(1)  # Will be None if no class is specified
                function_name = match.group(2)
                start_line = line_num + 1  # converting to 1-indexed line number
                
                # Search for opening brace in subsequent lines
                found_opening_brace = False
                brace_line = line_num
                param_level = line.count('(') - line.count(')')  # Track nested parentheses
                
                # Continue until we find the opening brace after the full signature
                while brace_line < total_lines - 1 and not found_opening_brace:
                    brace_line += 1
                    current_line = lines[brace_line]
                    
                    # Update parenthesis nesting level
                    param_level += current_line.count('(') - current_line.count(')')
                    
                    # Skip lines while we're still within function parameters
                    if param_level > 0:
                        continue
                    
                    # Check if the line contains the opening brace for function body
                    if '{' in current_line and ';' not in current_line:
                        found_opening_brace = True
                        line_num = brace_line  # Update line_num to the brace line
                        
                        brace_count = current_line.count('{') - current_line.count('}')
                        end_line = brace_line + 1
                        
                        # Continue scanning subsequent lines until braces are balanced
                        while brace_count > 0 and line_num < total_lines - 1:
                            line_num += 1
                            current_line = lines[line_num]
                            brace_count += current_line.count('{')
                            brace_count -= current_line.count('}')
                            end_line = line_num + 1
                        
                        new_func = {"class": class_name, "name": function_name, "start_line": start_line, "end_line": end_line}
                        functions.append(new_func)
                        break
                    
                    # If we hit a semicolon, this is a declaration, not a definition
                    elif ';' in current_line:
                        break

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