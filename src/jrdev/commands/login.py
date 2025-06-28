import uuid
import webbrowser
import time
import requests

from jrdev.commands.command_container import command_container
from jrdev.commands.provider import CommandProvider

@command_container.command()
class LoginCommand(CommandProvider):
    """
    Login to jrdev.
    """

    def handle(self, args: list[str]) -> None:
        """
        Handle the login command.
        """
        device_id = str(uuid.uuid4())
        login_url = f"http://localhost:8080/cli-login?device_id={device_id}"
        
        print("Please log in to your jrdev account in the browser window that just opened.")
        webbrowser.open(login_url)

        # Poll for the token
        token = None
        while token is None:
            try:
                response = requests.get(f"http://localhost:8080/cli-login-status?device_id={device_id}")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        token = data.get("token")
                        print("Login successful!")
                else:
                    time.sleep(2)
            except requests.exceptions.ConnectionError:
                print("Waiting for server...")
                time.sleep(2)

        # TODO: Store the token securely
        print(f"Your token is: {token}")


    def get_name(self) -> str:
        return "login"
