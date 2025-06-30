import aiohttp
# base_url = "https://jrdev-web-261022528192.us-central1.run.app"
base_url = "http://localhost:8080"  # Adjust this to your local server URL for testing

async def report_token_usage(app: any, model: str, tokens: int) -> None:
    """
    Report token usage to the jrdev-web server.
    """
    token = app.get_token() # I am assuming the app has a way to get the token
    if not token:
        app.ui.print_text("Not logged in. Please run /login first.", print_type="ERROR")
        return

    url = f"{base_url}/api/tokens"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"model": model, "tokens": tokens}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 204:
                    app.logger.error(f"Failed to report token usage: {response.status}")
                    app.ui.print_text("Failed to report token usage.", print_type="ERROR")
        except aiohttp.ClientConnectorError as e:
            app.logger.error(f"Failed to connect to server: {e}")
            app.ui.print_text("Failed to connect to server.", print_type="ERROR")
