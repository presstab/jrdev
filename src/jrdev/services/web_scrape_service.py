import httpx
from markdownify import markdownify as md

class WebScrapeService:
    def __init__(self):
        pass

    async def fetch_and_convert(self, url: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            html_content = response.text
            markdown_content = md(html_content)
            return markdown_content