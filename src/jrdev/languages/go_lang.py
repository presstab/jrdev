import re

from jrdev.languages.lang_base import Lang


class GoLang(Lang):
    def __init__(self):
        super().__init__("go")

    def parse_signature(self, signature):
        """
        Parse a Go function signature to extract package/struct and function name.

        Args:
            signature: Function signature string like "StructName.MethodName" or "packageName.FunctionName"

        Returns:
            Tuple of (struct_name, function_name)
        """
        parts = signature.split('.')
        if len(parts) > 1:
            # Handle struct methods: "StructName.MethodName"
            struct_name = parts[0]
            function_name = parts[1]
            return struct_name, function_name
        else:
            # Handle package-level functions: "functionName"
            return None, signature

    def is_control_structure(self, name):
        """Check if the identified name is a control structure and not a function."""
        control_structures = ["if", "for", "switch", "select", "case", "default"]
        return name.lower() in control_structures

    def find_function_end(self, lines, start_idx, brace_level):
        """
        Find the end of a function by tracking brace levels.

        Args:
            lines: List of file lines
            start_idx: Starting line index
            brace_level: Initial brace level

        Returns:
            Line index where the function ends
        """
        line_idx = start_idx
        total_lines = len(lines)

        while line_idx < total_lines:
            line = lines[line_idx]
            brace_level += line.count('{')
            brace_level -= line.count('}')

            if brace_level <= 0:
                return line_idx  # Found the end

            line_idx += 1

        # If we reach here, couldn't find the end, return last line
        return total_lines - 1

    def parse_functions(self, filepath):
        """
        Parse Go file to find function definitions and their locations.

        Args:
            filepath: Path to the Go file

        Returns:
            List of dicts with struct, name, start_line, and end_line for each function
        """
        with open(filepath, 'r') as f:
            lines = f.readlines()

        functions = []
        line_idx = 0
        total_lines = len(lines)

        # Regular expressions for Go parsing
        struct_pattern = re.compile(r'^\s*type\s+(\w+)\s+struct\s*{')
        method_pattern = re.compile(r'^\s*func\s+\((?:[^)]+)\s+\*?(\w+)\)\s+(\w+)')
        function_pattern = re.compile(r'^\s*func\s+(\w+)\s*\(')

        # Track current struct context
        current_struct = None

        while line_idx < total_lines:
            line = lines[line_idx]

            # Check for struct definition
            struct_match = struct_pattern.match(line)
            if struct_match:
                current_struct = struct_match.group(1)
                # Skip to end of struct definition
                brace_level = line.count('{')
                while brace_level > 0 and line_idx < total_lines - 1:
                    line_idx += 1
                    line = lines[line_idx]
                    brace_level += line.count('{')
                    brace_level -= line.count('}')
                line_idx += 1
                continue

            # Check for method definition (func with receiver)
            method_match = method_pattern.match(line)
            if method_match:
                receiver_struct = method_match.group(1)
                method_name = method_match.group(2)

                if not self.is_control_structure(method_name):
                    # Found a valid method
                    method_start = line_idx + 1  # 1-indexed
                    brace_level = line.count('{')

                    # If opening brace is not on this line, find it in subsequent lines
                    if '{' not in line:
                        search_idx = line_idx + 1
                        while search_idx < total_lines:
                            if '{' in lines[search_idx]:
                                brace_level += lines[search_idx].count('{')
                                break
                            search_idx += 1

                    # Find the end of the method
                    method_end_idx = self.find_function_end(lines, line_idx + 1, brace_level)
                    method_end = method_end_idx + 1  # 1-indexed

                    # Add the method to our functions list
                    functions.append({
                        'class': receiver_struct,
                        'name': method_name,
                        'start_line': method_start,
                        'end_line': method_end
                    })

                    # Update position
                    line_idx = method_end_idx

            # Check for function definition
            else:
                function_match = function_pattern.match(line)
                if function_match:
                    function_name = function_match.group(1)

                    if not self.is_control_structure(function_name):
                        # Found a valid function
                        function_start = line_idx + 1  # 1-indexed
                        brace_level = line.count('{')

                        # If opening brace is not on this line, find it in subsequent lines
                        if '{' not in line:
                            search_idx = line_idx + 1
                            while search_idx < total_lines:
                                if '{' in lines[search_idx]:
                                    brace_level += lines[search_idx].count('{')
                                    break
                                search_idx += 1

                        # Find the end of the function
                        function_end_idx = self.find_function_end(lines, line_idx + 1, brace_level)
                        function_end = function_end_idx + 1  # 1-indexed

                        # Add the function to our functions list
                        functions.append({
                            'class': None,
                            'name': function_name,
                            'start_line': function_start,
                            'end_line': function_end
                        })

                        # Update position
                        line_idx = function_end_idx

            line_idx += 1

        return functions
