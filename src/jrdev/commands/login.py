import asyncio
import uuid
import webbrowser
import aiohttp
from typing import Any, List

from jrdev.ui.ui import PrintType

async def handle_login(app: Any, _args: List[str], _worker_id: str) -> None:
    """
    Handle the login command.
    """
    device_id = str(uuid.uuid4())
    login_url = f"http://localhost:8080/login?device_id={device_id}"
    
    app.ui.print_text("Please log in to your jrdev account in the browser window that just opened.", PrintType.INFO)
    webbrowser.open(login_url)

    # Poll for the token
    token = None
    async with aiohttp.ClientSession() as session:
        while token is None:
            try:
                async with session.get(f"http://localhost:8080/cli-login-status?device_id={device_id}") as response:
                    app.logger.info(f"Response: {response}")
                    if response.status == 200:
                        data = await response.json()
                        token = data.get("token")
                        app.ui.print_text("Login successful!", PrintType.SUCCESS)
                    else:
                        await asyncio.sleep(2)
            except aiohttp.ClientConnectorError:
                app.ui.print_text("Waiting for server...", PrintType.INFO)
                await asyncio.sleep(2)

    # TODO: Store the token securely
    app.ui.print_text(f"Your token is: {token}", PrintType.INFO)
