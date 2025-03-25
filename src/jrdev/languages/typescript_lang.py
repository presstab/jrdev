import re

from jrdev.languages.lang_base import Lang


class TypeScriptLang(Lang):
    def __init__(self):
        super().__init__("typescript")

    # Regular expressions for TypeScript parsing
    CLASS_PATTERN = re.compile(r'^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)')
    METHOD_PATTERN = re.compile(
        r'^\s*(?:private\s+|public\s+|protected\s+|static\s+|async\s+|get\s+|set\s+)*(\w+)\s*' +
        r'(?:<[^>]*>)?\s*\([^{]*\)\s*(?::\s*[^{]+)?\s*{',
        re.DOTALL
    )
    FUNCTION_PATTERN = re.compile(
        r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)',
        re.DOTALL
    )
    CONTROL_STRUCTURES = ["if", "for", "while", "switch", "catch"]

    def parse_signature(self, signature):
        """
        Parse a TypeScript function signature to extract class and function name.

        Args:
            signature: Function signature string like "ClassName.methodName" or "functionName"

        Returns:
            Tuple of (class_name, function_name)
        """
        parts = signature.split('.')
        if len(parts) > 1:
            # Handle class methods: "ClassName.methodName"
            class_name = parts[0]
            function_name = parts[1]
            return class_name, function_name
        else:
            # Handle module-level functions: "functionName"
            return None, signature

    def is_control_structure(self, name):
        """Check if the identified name is a control structure and not a method."""
        return name in self.CONTROL_STRUCTURES

    def find_function_end(self, lines, start_idx, brace_level):
        """
        Find the end of a function/method by tracking brace levels.

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

    def process_class_method(self, lines, line_idx, current_class, functions):
        """
        Process a potential class method and add it to the functions list if valid.

        Args:
            lines: List of file lines
            line_idx: Current line index
            current_class: Current class context
            functions: List to append functions to

        Returns:
            Tuple of (new_line_idx, in_method, method_name, method_start)
        """
        line = lines[line_idx]
        method_match = self.METHOD_PATTERN.match(line)

        if not method_match:
            return line_idx, False, "", 0

        method_name = method_match.group(1)

        # Skip if this is a control structure
        if self.is_control_structure(method_name):
            return line_idx, False, "", 0

        # Found a valid method
        method_start = line_idx + 1  # 1-indexed
        brace_level = line.count('{')

        # Find the end of the method
        method_end_idx = self.find_function_end(lines, line_idx + 1, brace_level)
        method_end = method_end_idx + 1  # 1-indexed

        # Add the method to our functions list
        functions.append({
            'class': current_class,
            'name': method_name,
            'start_line': method_start,
            'end_line': method_end
        })

        # Return updated position
        return method_end_idx, False, "", 0

    def process_standalone_function(self, lines, line_idx, functions):
        """
        Process a potential standalone function and add it to the functions list if valid.

        Args:
            lines: List of file lines
            line_idx: Current line index
            functions: List to append functions to

        Returns:
            Tuple of (new_line_idx, in_method, method_name, method_start)
        """
        line = lines[line_idx]
        function_match = self.FUNCTION_PATTERN.match(line)

        if not function_match:
            return line_idx, False, "", 0

        function_name = function_match.group(1)
        function_start = line_idx + 1  # 1-indexed
        brace_level = line.count('{')

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

        # Return updated position
        return function_end_idx, False, "", 0

    def parse_functions(self, filepath):
        """
        Parse TypeScript file to find function definitions and their locations.

        Args:
            filepath: Path to the TypeScript file

        Returns:
            List of dicts with class, name, start_line, and end_line for each function
        """
        with open(filepath, 'r') as f:
            lines = f.readlines()

        functions = []
        current_class = None
        line_idx = 0
        total_lines = len(lines)

        while line_idx < total_lines:
            line = lines[line_idx]

            # Check for class definition
            class_match = self.CLASS_PATTERN.match(line)
            if class_match:
                current_class = class_match.group(1)
                line_idx += 1
                continue

            # Check for end of class
            if current_class and line.strip() == '}':
                current_class = None
                line_idx += 1
                continue

            # Process class method if we're in a class
            if current_class:
                new_idx, in_method, method_name, method_start = self.process_class_method(
                    lines, line_idx, current_class, functions
                )

                if new_idx != line_idx:
                    line_idx = new_idx + 1
                    continue

            # Process standalone function if not in a class
            if not current_class:
                new_idx, in_method, method_name, method_start = self.process_standalone_function(
                    lines, line_idx, functions
                )

                if new_idx != line_idx:
                    line_idx = new_idx + 1
                    continue

            # Move to next line if no matches
            line_idx += 1

        return functions
