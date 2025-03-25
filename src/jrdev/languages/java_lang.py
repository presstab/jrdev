import re

from jrdev.languages.lang_base import Lang


class JavaLang(Lang):
    def __init__(self):
        super().__init__("java")

    def parse_signature(self, signature):
        """
        Parse a Java function signature to extract class and method name.

        Args:
            signature: Function signature string like "ClassName.methodName" or "package.ClassName.methodName"

        Returns:
            Tuple of (class_name, method_name)
        """
        parts = signature.split('.')
        if len(parts) > 1:
            # Handle method in class: "ClassName.methodName" or "package.ClassName.methodName"
            if len(parts) == 2:
                # Simple "ClassName.methodName"
                class_name = parts[0]
                method_name = parts[1]
            else:
                # Handle fully qualified names like "package.ClassName.methodName"
                # For this simple case, we'll use the last two parts
                class_name = parts[-2]
                method_name = parts[-1]
            return class_name, method_name
        else:
            # This is rare in Java but could be a static import or similar
            return None, signature

    def find_matching_brace(self, lines, start_idx, initial_level=0):
        """
        Find the matching closing brace by tracking brace levels.

        Args:
            lines: List of file lines
            start_idx: Starting line index
            initial_level: Initial brace level (usually 0 or 1)

        Returns:
            Line index where the matching brace is found
        """
        brace_level = initial_level
        line_idx = start_idx
        total_lines = len(lines)

        # Handle case where we're already looking at the first line that contains a brace
        brace_level += lines[start_idx].count('{')
        brace_level -= lines[start_idx].count('}')

        # If we already found the end on the first line, return it
        if brace_level <= 0 and initial_level > 0:
            return line_idx

        # Continue searching in subsequent lines
        line_idx += 1

        while line_idx < total_lines:
            line = lines[line_idx]
            brace_level += line.count('{')
            brace_level -= line.count('}')

            if brace_level <= 0:
                return line_idx  # Found the matching brace

            line_idx += 1

        # If we reach here, couldn't find the end, return last line
        return total_lines - 1

    def parse_functions(self, filepath):
        """
        Parse Java file to find method definitions and their locations.

        Args:
            filepath: Path to the Java file

        Returns:
            List of dicts with class, name, start_line, and end_line for each method
        """
        with open(filepath, 'r') as f:
            lines = f.readlines()

        methods = []
        line_idx = 0
        total_lines = len(lines)

        # Track current class/interface/enum context
        current_class = None
        class_brace_stack = []

        # Regular expressions
        # Match class, interface, enum, and record declarations
        class_pattern = re.compile(r'^\s*(public|private|protected)?\s*(abstract|final|static)?\s*(class|interface|enum|record)\s+(\w+)')

        # Match method declarations, capturing modifiers, return type, method name and parameters
        # This handles various formats of Java method declarations
        method_pattern = re.compile(r'^\s*((?:public|private|protected|static|final|abstract|synchronized|native|transient|volatile|strictfp|\s)+)?\s*(?:<[^>]+>\s*)?(?:(\w+(?:\[\s*\])*|\w+\s*<[^>]+>)\s+)?(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s.]+)?\s*(?:;|{)')

        # Pattern to skip constructors when searching for methods
        constructor_pattern = re.compile(r'^\s*((?:public|private|protected)?\s*(?:[\w<>\s,]+))?\s*(\w+)\s*\(')

        while line_idx < total_lines:
            line = lines[line_idx]

            # Check for class, interface or enum declaration
            class_match = class_pattern.match(line)
            if class_match:
                class_type = class_match.group(3)  # 'class', 'interface', 'enum', or 'record'
                class_name = class_match.group(4)
                current_class = class_name

                # Find opening brace
                brace_idx = line.find('{')
                if brace_idx != -1:
                    # Opening brace on same line
                    class_brace_stack.append(line_idx)
                else:
                    # Search for opening brace on subsequent lines
                    search_idx = line_idx + 1
                    while search_idx < total_lines:
                        if '{' in lines[search_idx]:
                            class_brace_stack.append(search_idx)
                            break
                        search_idx += 1

                # Move to next line
                line_idx += 1
                continue

            # If we're not within a class definition, skip this line
            if current_class is None:
                line_idx += 1
                continue

            # Check for method declaration
            method_match = method_pattern.match(line)
            if method_match and ');' not in line:  # Skip method declarations without bodies (interface methods that end with ';')
                # Check if this is actually a constructor by comparing method name with class name
                constructor_match = constructor_pattern.match(line)
                method_name = method_match.group(3)

                # Filter out false positives that might be local variable declarations or if/for/while statements
                control_keywords = ['if', 'for', 'while', 'switch', 'catch']
                if method_name in control_keywords:
                    line_idx += 1
                    continue

                is_constructor = constructor_match and constructor_match.group(2) == current_class

                if '{' in line:
                    # Method body starts on the same line
                    method_start = line_idx + 1  # 1-indexed
                    method_end_idx = self.find_matching_brace(lines, line_idx, line.count('{'))
                    method_end = method_end_idx + 1  # 1-indexed

                    methods.append({
                        'class': current_class,
                        'name': method_name,
                        'start_line': method_start,
                        'end_line': method_end
                    })

                    # Update position
                    line_idx = method_end_idx + 1
                    continue
                else:
                    # Method declaration spans multiple lines, find the opening brace
                    search_idx = line_idx + 1
                    found_brace = False

                    while search_idx < total_lines:
                        if '{' in lines[search_idx]:
                            found_brace = True
                            break

                        # If we hit a semicolon before a brace, this might be an interface method declaration
                        if ';' in lines[search_idx]:
                            found_brace = False
                            break

                        search_idx += 1

                    if found_brace:
                        method_start = line_idx + 1  # 1-indexed
                        method_end_idx = self.find_matching_brace(lines, search_idx, 0)
                        method_end = method_end_idx + 1  # 1-indexed

                        methods.append({
                            'class': current_class,
                            'name': method_name,
                            'start_line': method_start,
                            'end_line': method_end
                        })

                        # Update position
                        line_idx = method_end_idx + 1
                        continue

            # Check for end of class
            if line.strip() == '}' and class_brace_stack:
                class_brace_stack.pop()

                # If all class braces are closed, we're out of any class
                if not class_brace_stack:
                    current_class = None

            line_idx += 1

        return methods
