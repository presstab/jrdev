import aiohttp
# base_url = "https://jrdev-web-261022528192.us-central1.run.app"
base_url = "http://localhost:8080"  # Adjust this to your local server URL for testing

async def report_token_usage(app: any, model: str, tokens: int) -> None:
    """
    Report token usage to the jrdev-web server.
    """
    id_token = app.get_id_token()
    refresh_token = app.get_refresh_token()
    device_id = app.get_device_id()
    if not id_token or not refresh_token or not device_id:
        app.ui.print_text("Not logged in. Please run /login first.", print_type="ERROR")
        return

    url = f"{base_url}/api/tokens"
    headers = {
        "X-ID-Token": id_token,
        "X-Refresh-Token": refresh_token,
        "X-Device-ID": device_id,
    }
    data = {"model": model, "tokens": tokens}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 204:
                    error_text = await response.text()
                    app.logger.error(f"Failed to report token usage: {response.status} {error_text}")
                    app.ui.print_text(f"Failed to report token usage. Status: {response.status}, Info: {error_text}", print_type="ERROR")
        except aiohttp.ClientConnectorError as e:
            app.logger.error(f"Failed to connect to server: {e}")
            app.ui.print_text(f"Failed to connect to server to report token usage: {e}", print_type="ERROR")
