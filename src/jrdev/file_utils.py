import re


def is_requesting_files(text):
    return re.search(r"get_files\s+(\[.*?\])", text, re.DOTALL)
