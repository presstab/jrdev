from typing import Any, Dict, List

from ddgs import DDGS

class WebSearchService:
    def __init__(self):
        self.engine = DDGS(timeout=5)

    def search(self, query: str) -> List[Dict[str, Any]]:
        return self.engine.text(query=query, max_results=10)