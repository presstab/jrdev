import re

from jrdev.languages.lang_base import Lang


class CppLang(Lang):
    def __init__(self):
        super().__init__("cpp")

    def parse_functions(self, file_path):
        """
        Parse a C++ file to find function definitions and declarations with their locations.

        Args:
            file_path: Path to the C++ file

        Returns:
            List of dicts with class, name, start_line, and end_line for each function
        """
        # First pattern to detect start of function definition (with or without class scope)
        func_start_regex = re.compile(
            r'^\s*(?:[\w:&*<>\s]+\s+)?(?:(\w+)::)?(~?\w+)\s*\([^{;]*$'
        )

        # Pattern for function declarations that are all on one line
        inline_func_regex = re.compile(
            r'^\s*(?:[\w:&*<>\s]+\s+)?(?:(\w+)::)?(~?\w+)\s*\([^{;]*\)\s*(?:const|override|final|noexcept|=\s*default|=\s*delete|\s)*\s*\{'
        )

        # Pattern to detect function declarations in header files (ending with semicolon)
        func_decl_regex = re.compile(
            r'^\s*(?:virtual\s+|static\s+|explicit\s+|inline\s+|constexpr\s+)*(?:[\w:&*<>\s]+\s+)?(?:(?:(\w+)::)?)?(~?\w+)\s*\([^)]*\)(?:\s*(?:const|override|final|noexcept|=\s*default|=\s*delete|\s)*)*\s*;'
        )

        with open(file_path, 'r') as f:
            lines = f.readlines()

        functions = []
        total_lines = len(lines)
        line_num = 0  # index starting at 0
        inside_class = None  # Track current class context

        # First pass - detect class contexts
        class_stack = []
        class_regex = re.compile(r'^\s*class\s+(\w+)(?:\s*:\s*(?:public|protected|private)\s+[\w:]+(?:\s*,\s*(?:public|protected|private)\s+[\w:]+)*)?(?:\s*\{)?')

        # Process the file to identify all class definitions and their scopes
        brace_level = 0
        current_class = None
        class_scopes = []

        for i, line in enumerate(lines):
            # Detect class definitions
            class_match = class_regex.match(line)
            if class_match and ";" not in line:  # Avoid forward declarations
                class_name = class_match.group(1)
                current_class = class_name
                class_start = i+1

                # If the opening brace is on this line, start counting
                if "{" in line:
                    brace_level += line.count("{")

            # Track brace levels to determine class scope
            if current_class:
                if "{" in line:
                    brace_level += line.count("{")
                if "}" in line:
                    brace_level -= line.count("}")

                # If braces balance out at the end of a class
                if brace_level == 0 and "}" in line:
                    class_scopes.append({
                        "name": current_class,
                        "start": class_start,
                        "end": i+1
                    })
                    current_class = None

        # Second pass - find all functions
        while line_num < total_lines:
            line = lines[line_num]

            # Determine current class context based on line number
            line_num_1based = line_num + 1  # Convert to 1-indexed for comparison
            current_class = None
            for scope in class_scopes:
                if scope["start"] <= line_num_1based <= scope["end"]:
                    current_class = scope["name"]
                    break

            # Check if we're in a class declaration block (between class and first {)
            if not current_class:
                # Check for class declaration context (before opening brace)
                class_decl_match = re.search(r'^\s*class\s+(\w+)', line)
                if class_decl_match:
                    # We're at a class declaration line
                    current_class = class_decl_match.group(1)

            # Try to match inline function definition first
            match = inline_func_regex.match(line)
            if match:
                class_name = match.group(1) or current_class  # Use detected class if none in signature
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

            # Try to match function declaration (header files)
            elif func_decl_regex.match(line):
                match = func_decl_regex.match(line)
                class_name = match.group(1) or current_class  # Use detected class if none in signature
                function_name = match.group(2)
                start_line = line_num + 1  # converting to 1-indexed line number
                end_line = start_line  # For declarations, end_line is the same as start_line

                new_func = {"class": class_name, "name": function_name, "start_line": start_line, "end_line": end_line}
                functions.append(new_func)

            # Try to match multi-line function definition
            else:
                match = func_start_regex.match(line)
                if match:
                    class_name = match.group(1) or current_class  # Use detected class if none in signature
                    function_name = match.group(2)
                    start_line = line_num + 1  # converting to 1-indexed line number

                    # Search for opening brace or semicolon in subsequent lines
                    found_ending = False
                    search_line = line_num
                    param_level = line.count('(') - line.count(')')  # Track nested parentheses

                    # Continue until we find the opening brace or semicolon after the full signature
                    while search_line < total_lines - 1 and not found_ending:
                        search_line += 1
                        current_line = lines[search_line]

                        # Update parenthesis nesting level
                        param_level += current_line.count('(') - current_line.count(')')

                        # Skip lines while we're still within function parameters
                        if param_level > 0:
                            continue

                        # Check if the line contains the opening brace for function body
                        if '{' in current_line and ';' not in current_line:
                            found_ending = True
                            line_num = search_line  # Update line_num to the brace line

                            brace_count = current_line.count('{') - current_line.count('}')
                            end_line = search_line + 1

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

                        # If we hit a semicolon, this is a declaration - still add it!
                        elif ';' in current_line:
                            found_ending = True
                            end_line = search_line + 1  # For declarations, end_line is at the semicolon

                            new_func = {"class": class_name, "name": function_name, "start_line": start_line, "end_line": end_line}
                            functions.append(new_func)
                            break

            line_num += 1

        return functions

    def parse_signature(self, signature):
        """
        Parse a C++ function signature to extract class and function name.

        Args:
            signature: Function signature string like "ClassName::functionName" or just "functionName"

        Returns:
            Tuple of (class_name, function_name)
        """
        # Handle empty input
        if not signature:
            return None, ""

        # First check if the signature contains a class scope operator
        if '::' in signature:
            # This regex captures the class name and function name.
            # It handles cases where the function name might be a destructor (starting with ~).
            pattern = re.compile(r'^\s*([a-zA-Z_]\w*)::(~?[a-zA-Z_]\w*)\s*\(')
            match = pattern.match(signature)
            if match:
                class_name = match.group(1)
                function_name = match.group(2)
                return class_name, function_name

            # If pattern didn't match but there's a :: operator, try simpler extraction
            parts = signature.split('::', 1)  # Split on first occurrence only
            if len(parts) == 2:
                class_name = parts[0].strip()
                # Extract function name, removing any parameters if present
                function_name = parts[1].split('(')[0].strip()
                return class_name, function_name
        else:
            # If no class scope operator, this is just a function name
            # Extract function name, removing any parameters if present
            function_name = signature.split('(')[0].strip()
            return None, function_name

        # If all extraction methods failed
        return None, None
