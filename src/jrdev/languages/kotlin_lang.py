import re

from jrdev.languages.lang_base import Lang


class KotlinLang(Lang):
    def __init__(self):
        super().__init__("kotlin")

    def parse_signature(self, signature):
        """
        Parse a Kotlin function signature to extract class and function name.

        Args:
            signature: Function signature string like "ClassName.functionName" or "package.ClassName.functionName"

        Returns:
            Tuple of (class_name, function_name)
        """
        parts = signature.split('.')
        if len(parts) > 1:
            # Handle method in class: "ClassName.methodName" or "package.ClassName.methodName"
            if len(parts) == 2:
                # Simple "ClassName.methodName"
                class_name = parts[0]
                function_name = parts[1]
            else:
                # Handle fully qualified names like "package.ClassName.methodName"
                # For this simple case, we'll use the last two parts
                class_name = parts[-2]
                function_name = parts[-1]
            return class_name, function_name
        else:
            # This could be a top-level function or an extension function
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
        Parse Kotlin file to find function definitions and their locations.

        Args:
            filepath: Path to the Kotlin file

        Returns:
            List of dicts with class, name, start_line, and end_line for each function
        """
        with open(filepath, 'r') as f:
            lines = f.readlines()

        functions = []
        line_idx = 0
        total_lines = len(lines)

        # Track current class/object/interface context
        current_class = None
        class_brace_stack = []

        # Regular expressions for Kotlin parsing
        # Match class, object, interface declarations
        class_pattern = re.compile(r'^\s*(open|abstract|sealed|data|enum)?\s*(class|object|interface)\s+(\w+)')

        # Match function declarations, including those with various modifiers and return types
        function_pattern = re.compile(r'^\s*((?:public|private|protected|internal|open|abstract|override|suspend|inline|external|operator|infix|tailrec|\s)+)?\s*fun\s+(?:<[^>]+>\s*)?(?:[\w.]+\.)?\s*(\w+)\s*\(')

        # Match extension functions
        extension_pattern = re.compile(r'^\s*((?:public|private|protected|internal|open|abstract|override|suspend|inline|external|operator|infix|tailrec|\s)+)?\s*fun\s+(?:<[^>]+>\s*)?(\w+(?:\.\w+)*)\s*\.\s*(\w+)\s*\(')

        while line_idx < total_lines:
            line = lines[line_idx]

            # Skip comments
            if line.strip().startswith("//") or line.strip().startswith("/*"):
                line_idx += 1
                continue

            # Check for class, object or interface declaration
            class_match = class_pattern.match(line)
            if class_match:
                class_type = class_match.group(2)  # 'class', 'object', or 'interface'
                class_name = class_match.group(3)
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

            # Check for extension function
            extension_match = extension_pattern.match(line)
            if extension_match:
                receiver_type = extension_match.group(2)
                function_name = extension_match.group(3)

                # Find the function body
                if '{' in line:
                    # Function body starts on the same line
                    func_start = line_idx + 1  # 1-indexed
                    func_end_idx = self.find_matching_brace(lines, line_idx, line.count('{'))
                    func_end = func_end_idx + 1  # 1-indexed

                    functions.append({
                        'class': receiver_type,  # Use receiver type as "class"
                        'name': function_name,
                        'start_line': func_start,
                        'end_line': func_end
                    })

                    # Update position
                    line_idx = func_end_idx + 1
                    continue
                else:
                    # Function declaration spans multiple lines, find the opening brace
                    search_idx = line_idx + 1
                    found_brace = False

                    while search_idx < total_lines:
                        if '{' in lines[search_idx]:
                            found_brace = True
                            break

                        # If we hit an equals sign before a brace, this might be a single-expression function
                        if '=' in lines[search_idx] and '{' not in lines[search_idx]:
                            # Single-expression function, find the end (marked by line with less indentation)
                            start_indent = len(line) - len(line.lstrip())
                            expr_idx = search_idx
                            while expr_idx < total_lines - 1:
                                next_line = lines[expr_idx + 1]
                                if next_line.strip() and len(next_line) - len(next_line.lstrip()) <= start_indent:
                                    break
                                expr_idx += 1

                            functions.append({
                                'class': receiver_type,
                                'name': function_name,
                                'start_line': line_idx + 1,  # 1-indexed
                                'end_line': expr_idx + 1     # 1-indexed
                            })

                            # Update position and continue outer loop
                            line_idx = expr_idx + 1
                            found_brace = False
                            break

                        search_idx += 1

                    if found_brace:
                        func_start = line_idx + 1  # 1-indexed
                        func_end_idx = self.find_matching_brace(lines, search_idx, 0)
                        func_end = func_end_idx + 1  # 1-indexed

                        functions.append({
                            'class': receiver_type,
                            'name': function_name,
                            'start_line': func_start,
                            'end_line': func_end
                        })

                        # Update position
                        line_idx = func_end_idx + 1
                        continue

            # Check for regular function declaration (not extension)
            function_match = function_pattern.match(line)
            if function_match:
                function_name = function_match.group(2)

                # Filter out control keywords that might be misidentified
                control_keywords = ['if', 'for', 'while', 'when']
                if function_name in control_keywords:
                    line_idx += 1
                    continue

                # Find the function body
                if '{' in line:
                    # Function body starts on the same line
                    func_start = line_idx + 1  # 1-indexed
                    func_end_idx = self.find_matching_brace(lines, line_idx, line.count('{'))
                    func_end = func_end_idx + 1  # 1-indexed

                    functions.append({
                        'class': current_class,
                        'name': function_name,
                        'start_line': func_start,
                        'end_line': func_end
                    })

                    # Update position
                    line_idx = func_end_idx + 1
                    continue
                else:
                    # Function declaration spans multiple lines, find the opening brace
                    search_idx = line_idx + 1
                    found_brace = False

                    while search_idx < total_lines:
                        if '{' in lines[search_idx]:
                            found_brace = True
                            break

                        # If we hit an equals sign before a brace, this might be a single-expression function
                        if '=' in lines[search_idx] and '{' not in lines[search_idx]:
                            # Single-expression function, find the end (marked by line with less indentation)
                            start_indent = len(line) - len(line.lstrip())
                            expr_idx = search_idx
                            while expr_idx < total_lines - 1:
                                next_line = lines[expr_idx + 1]
                                if next_line.strip() and len(next_line) - len(next_line.lstrip()) <= start_indent:
                                    break
                                expr_idx += 1

                            functions.append({
                                'class': current_class,
                                'name': function_name,
                                'start_line': line_idx + 1,  # 1-indexed
                                'end_line': expr_idx + 1     # 1-indexed
                            })

                            # Update position and continue outer loop
                            line_idx = expr_idx + 1
                            found_brace = False
                            break

                        search_idx += 1

                    if found_brace:
                        func_start = line_idx + 1  # 1-indexed
                        func_end_idx = self.find_matching_brace(lines, search_idx, 0)
                        func_end = func_end_idx + 1  # 1-indexed

                        functions.append({
                            'class': current_class,
                            'name': function_name,
                            'start_line': func_start,
                            'end_line': func_end
                        })

                        # Update position
                        line_idx = func_end_idx + 1
                        continue

            # Check for end of class
            if line.strip() == '}' and class_brace_stack:
                class_brace_stack.pop()

                # If all class braces are closed, we're out of any class
                if not class_brace_stack:
                    current_class = None

            line_idx += 1

        return functions
