

# language base class
class Lang:
    def __init__(self, _language_name):
        self.language_name = _language_name

    def parse_functions(self, file_path):
        raise NotImplementedError(f"parse_functions not implemented for {self.language_name}")

    def parse_signature(self, signature: str):
        raise NotImplementedError(f"parse_signature not implemented for {self.language_name}")
