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
    app.set_device_id(device_id)
    base_url = "https://jrdev-web-261022528192.us-central1.run.app"
    # base_url = "http://localhost:8080"  # Adjust this to your local server URL for testing
    login_url = f"{base_url}/login?device_id={device_id}"
    check_url = f"{base_url}/cli-login-status?device_id={device_id}"

    app.ui.print_text("Please log in to your jrdev account in the browser window that just opened.", PrintType.INFO)
    webbrowser.open(login_url)
    # Poll for the tokens with a max polling time of 2 minutes
    id_token = None
    refresh_token = None
    max_poll_time = 120  # seconds
    start_time = asyncio.get_event_loop().time()
    interval = 5  # seconds
    async with aiohttp.ClientSession() as session:
        while id_token is None:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_poll_time:
                app.ui.print_text("Login timed out. Please try again.", PrintType.ERROR)
                return
            try:
                async with session.get(check_url) as response:
                    app.logger.info(f"Response: {response}")
                    if response.status == 200:
                        data = await response.json()
                        id_token = data.get("id_token")
                        refresh_token = data.get("refresh_token")
                        if id_token and refresh_token:
                            app.set_auth_tokens(id_token, refresh_token)
                            app.ui.print_text("Login successful!", PrintType.SUCCESS)
                        else:
                            await asyncio.sleep(interval)
                    else:
                        await asyncio.sleep(interval)
            except aiohttp.ClientConnectorError:
                app.ui.print_text("Waiting for server...", PrintType.INFO)
                await asyncio.sleep(interval)

    if id_token and refresh_token:
        app.set_auth_tokens(id_token, refresh_token)
        app.ui.print_text("You are now logged in.", PrintType.SUCCESS)
    else:
        app.ui.print_text("Login failed. Please try again.", PrintType.ERROR)
