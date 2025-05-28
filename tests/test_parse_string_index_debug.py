#!/usr/bin/env python3
import sys
sys.path.append('/home/pt/workspace/jrdev')
from jrdev.file_operations.file_utils import manual_json_parse

# Load the test file
test_file_path = '/home/pt/workspace/jrdev/tests/mock/string_index_out_of_range.txt'

with open(test_file_path, 'r') as f:
    file_content = f.read()

print("File content:")
print(file_content)

# Add debug function to trace through parsing
def debug_manual_json_parse(text):
    """
    Debug version of manual_json_parse with print statements
    """
    print("Starting manual_json_parse")
    # Split the input text into non-empty lines.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    print(f"Extracted {len(lines)} non-empty lines")

    nums = "0123456789"
    pending_key = ""
    main_object = {}
    stack = []
    stack.append(main_object)

    quote_text = ""
    quote_open = False
    skip_colon = True

    for line_idx, line in enumerate(lines):
        print(f"\nProcessing line {line_idx}: {line}")

        # if line has markdown, remove it
        if "```json" in line:
            print(f"  Skipping markdown line: {line}")
            if len(line) == len("```json"):
                continue
            #todo handle if valid json is on same line

        num_start = -1

        # Check for boolean values in the line (enhancement we made earlier)
        true_match = "true" in line
        false_match = "false" in line
        if true_match or false_match:
            print(f"  Found boolean value: {true_match=}, {false_match=}")

        i = -1
        try:
            for char in line:
                i += 1
                print(f"  Char at {i}: '{char}' (pending_key={pending_key}, quote_open={quote_open}, num_start={num_start})")

                if char == ":" and skip_colon:
                    skip_colon = False
                    print(f"    Skip colon - continuing")
                    continue

                # Handle boolean literals (enhancement we made earlier)
                if pending_key and i + 4 <= len(line) and line[i:i+4] == "true":
                    print(f"    Processing boolean true")
                    stack[-1][pending_key] = True
                    pending_key = ""
                    i += 3  # Skip the rest of 'true'
                    continue
                if pending_key and i + 5 <= len(line) and line[i:i+5] == "false":
                    print(f"    Processing boolean false")
                    stack[-1][pending_key] = False
                    pending_key = ""
                    i += 4  # Skip the rest of 'false'
                    continue

                if char == "\"":
                    #check if it is escaped
                    is_escaped = i > 0 and line[i - 1] == "\\"
                    print(f"    Quote char: is_escaped={is_escaped}, quote_open={quote_open}")

                    if quote_open:
                        if is_escaped:
                            quote_text += "\""
                            print(f"    Added escaped quote to quote_text: {quote_text}")
                            continue

                        #close quote now
                        quote_open = False
                        print(f"    Closing quote, quote_text={quote_text}")

                        # this is either naming a new key or is a value, check next char
                        if i + 1 < len(line):
                            next_char = line[i+1]
                            print(f"    Next char after quote: '{next_char}'")
                            if next_char == ":":
                                #just named a value
                                pending_key = quote_text
                                quote_text = ""
                                print(f"    Named a key: pending_key={pending_key}")

                                skip_colon = True
                            elif pending_key:
                                #simple kv pair, and quote text is the value?
                                print(f"    Setting value for key {pending_key}={quote_text}")
                                stack[-1][pending_key] = quote_text
                                quote_text = ""
                                pending_key = ""
                            elif next_char == "," or next_char == "]":
                                # possible list of strings
                                if isinstance(stack[-1], list):
                                    print(f"    Adding string '{quote_text}' to list")
                                    stack[-1].append(quote_text)
                                    quote_text = ""
                                    continue
                                else:
                                    print(f"    ERROR: UNHANDLED QUOTE END - next_char={next_char}, stack[-1]={type(stack[-1])}")
                                    raise Exception("UNHANDLED QUOTE END")
                        else:
                            # last character of this line.. no comma end? probably last in a container?
                            print(f"    Quote at end of line")
                            if pending_key:
                                print(f"    Setting final value for key {pending_key}={quote_text}")
                                stack[-1][pending_key] = quote_text
                                quote_text = ""
                                pending_key = ""
                                continue
                            elif isinstance(stack[-1], list):
                                print(f"    Adding final string '{quote_text}' to list")
                                stack[-1].append(quote_text)
                                quote_text = ""
                                continue
                            else:
                                print(f"    ERROR: UNHANDLED QUOTE END - end of line, stack[-1]={type(stack[-1])}")
                                raise Exception("UNHANDLED QUOTE END 230")
                        continue
                    else:
                        #start of new quote
                        quote_open = True
                        print(f"    Starting new quote")
                        continue

                if quote_open:
                    #quote is open, just add to quote text
                    quote_text += char
                    print(f"    Added '{char}' to quote_text: {quote_text}")
                    continue

                if char in nums:
                    print(f"    Processing number char: {char}")
                    if num_start == -1:
                        num_start = i
                        print(f"    Starting new number at index {num_start}")

                    num_end = i

                    #check if this is last digit
                    if i + 1 < len(line):
                        if line[i+1] in nums:
                            print(f"    Next char is also number, continuing")
                            continue

                    #last instance, now compile as full number
                    num_str = line[num_start:(num_end+1)]
                    print(f"    Completed number: {num_str}")
                    num_start = -1
                    n = int(num_str)
                    if pending_key:
                        print(f"    Setting number value {n} for key {pending_key}")
                        stack[-1][pending_key] = n
                        pending_key = ""
                    elif isinstance(stack[-1], list):
                        print(f"    Adding number {n} to list")
                        stack[-1].append(n)
                    else:
                        error_msg = f"UNHANDLED NUMBER* 264*** {num_str}"
                        print(f"    ERROR: {error_msg}")
                        raise Exception(error_msg)
                    continue

                # object start
                if char == "{":
                    print(f"    Object start")
                    # new object
                    if not main_object:
                        # just start of main object
                        print(f"    Top-level object start")
                        continue

                    # is there a pending kv pair?
                    if pending_key:
                        print(f"    Creating new object for key {pending_key}")
                        obj_new = {}
                        stack[-1][pending_key] = obj_new
                        stack.append(obj_new)
                        pending_key = ""
                        continue

                    if isinstance(stack[-1], list):
                        # add new object to list
                        print(f"    Adding new object to list")
                        new_obj = {}
                        stack[-1].append(new_obj)
                        stack.append(new_obj)
                        continue

                if char == "[":
                    print(f"    Array start")
                    #new array
                    if pending_key:
                        print(f"    Creating new array for key {pending_key}")
                        new_list = []
                        stack[-1][pending_key] = new_list
                        stack.append(new_list)
                        pending_key = ""
                        continue
                if char == "]":
                    # end of array
                    print(f"    Array end")
                    assert isinstance(stack[-1], list)
                    stack.pop()
                    continue
                if char == "}":
                    # end of object
                    print(f"    Object end")
                    assert isinstance(stack[-1], dict)
                    stack.pop()
                    continue
        except Exception as e:
            print(f"Exception during processing of line {line_idx} at char {i}: {str(e)}")
            if i < len(line):
                context_start = max(0, i - 10)
                context_end = min(len(line), i + 10)
                context = line[context_start:context_end]
                pointer = ' ' * (min(10, i) - 1) + '^'
                print(f"Context: ...{context}...")
                print(f"Position:   {pointer}")
            raise

    print("\nFinal result:")
    import pprint
    pprint.pprint(main_object)
    return main_object

# Try to parse with debug version
print("\nAttempting to parse with debug version...")
try:
    result = debug_manual_json_parse(file_content)
    print("\nParsing succeeded!")
except Exception as e:
    print(f"\nParsing failed with exception: {str(e)}")