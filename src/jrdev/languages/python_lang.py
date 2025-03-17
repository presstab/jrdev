from jrdev.languages.lang_base import Lang

class PythonLang(Lang):
    def __init__(self):
        super().__init__("python")
    
    def parse_signature(self, signature):
        """
        Parse a Python function signature to extract class and function name.
        
        Args:
            signature: Function signature string like "ClassName.method_name" or "function_name"
            
        Returns:
            Tuple of (class_name, function_name)
        """
        parts = signature.split('.')
        if len(parts) > 1:
            # Handle class methods: "ClassName.method_name"
            class_name = parts[0]
            function_name = parts[1]
            return class_name, function_name
        else:
            # Handle module-level functions: "function_name"
            return None, signature
    
    def parse_functions(self, filepath):
        """
        Parse Python file to find function definitions and their locations.
        
        Args:
            filepath: Path to the Python file
            
        Returns:
            List of dicts with class, name, start_line, and end_line for each function
        """
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        functions = []
        in_class = None
        indentation_stack = [0]  # Stack to track indentation levels
        line_num = 0
        total_lines = len(lines)
        
        while line_num < total_lines:
            line = lines[line_num]
            stripped = line.lstrip()
            indentation = len(line) - len(stripped)
            
            # Check for class definition
            if stripped.startswith('class '):
                class_def = stripped[6:].split('(')[0].split(':')[0].strip()
                in_class = class_def
                indentation_stack.append(indentation)
            
            # Check for function definition
            elif stripped.startswith('def '):
                current_indentation = indentation
                
                # Extract function name
                func_name = stripped[4:].split('(')[0].strip()
                
                # Determine if this is a class method or a module function
                class_name = None
                if current_indentation > indentation_stack[-1]:
                    # Function is indented more than current context, likely a class method
                    class_name = in_class
                
                # Mark the start line (1-indexed)
                start_line = line_num + 1
                
                # Skip past the function definition line(s)
                line_num += 1
                
                # Find the end of the function
                while line_num < total_lines:
                    next_line = lines[line_num]
                    next_stripped = next_line.lstrip()
                    next_indentation = len(next_line) - len(next_stripped)
                    
                    # If we hit a line with less indentation than the function def, we've exited the function
                    if next_stripped and next_indentation <= current_indentation:
                        break
                    
                    line_num += 1
                
                # The end line is the last line we processed
                end_line = line_num
                
                # Add the function to our list
                functions.append({
                    'class': class_name,
                    'name': func_name,
                    'start_line': start_line,
                    'end_line': end_line
                })
                
                # Continue processing from current position (don't increment line_num)
                continue
            
            # Check if we're exiting a class
            elif stripped and indentation <= indentation_stack[-1] and in_class:
                # We've exited the current class
                in_class = None
                indentation_stack.pop()
            
            line_num += 1
        
        return functions