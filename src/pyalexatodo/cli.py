import asyncio
import json
import sys
from functools import wraps
from pathlib import Path
from typing import Any, cast

try:
    import keyring
    import orjson
    import typer
    from rich.console import Console
except ImportError:
    print("Required packages for CLI usage are not installed. Please install pyalexatodo[cli] to install them. "
          "For example with pip: pip install \"pyalexatodo[cli]\"")
    sys.exit(1)

from aioamazondevices import CannotAuthenticate, CannotConnect
from aioamazondevices.api import AmazonEchoApi
from aioamazondevices.exceptions import AmazonError, CannotRegisterDevice
from aiohttp import ClientSession

from pyalexatodo.api import AlexaToDoAPI
from pyalexatodo.exceptions import ItemNotFoundException
from pyalexatodo.models.cli_settings import CliSettings

app = typer.Typer()
console = Console()

# Global variables to hold the API client and default list ID after initialization
alexa_list_api: AlexaToDoAPI
client_session: ClientSession
default_list_id: str = ""

KEYRING_SERVICE = "alexalists-cli"
PASSWORD_KEY = "amazon-password"

### Helper functions for file I/O and API initialization ###

def read_from_file(data_file: str) -> dict[str, Any]:
    """Load stored login data from file."""
    if not data_file or not Path(data_file).exists():
        print(
            "Cannot find previous login data file: ",
            data_file,
        )
        return {}

    with open(Path(data_file), "r") as f:
        return cast("dict[str, Any]", json.loads(f.read()))


def save_to_file(
    raw_data: str | dict[str, Any],
    content_type: str = "application/json",
) -> None:
    """Save login_data data to disk."""
    if not raw_data:
        return

    try:
        fullpath = Path(get_outputpath("login_data.json"))

        # Create main output directory and timestamp subdirectory
        output_dir = fullpath.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert dict to JSON string if needed
        if isinstance(raw_data, dict):
            json_data = raw_data
        else:
            # Assume it's a JSON string
            json_data = orjson.loads(raw_data)

        data = orjson.dumps(
            json_data,
            option=orjson.OPT_INDENT_2,
        ).decode("utf-8")

        print(f"Saving data to {fullpath}")

        with open(fullpath, "w", encoding="utf-8") as file:
            file.write(data)
            file.write("\n")
    except Exception as e:
        print(f"Error saving login data: {e}")

def get_outputpath(filename: str) -> str:
    """Get the absolute path for storing application files.

    Args:t
        filename (str): The name of the file.

    Returns:
        str: The absolute path to the file in the user's home directory.
    """
    return Path(Path.home(), ".pyalexatodo", filename).as_posix()


async def init_api():
    """Initialize the Alexa API using stored credentials and settings.

    This function:
    1. Loads the CLI settings from the config file
    2. Retrieves credentials from the system keyring
    3. Initializes and tests the Alexa login
    4. Creates the API instance

    Returns:
        AlexaListAPI: An initialized API instance.

    Raises:
        FileNotFoundError: If the CLI settings file is not found.
        SystemExit: If login fails or settings are invalid.
    """
    global alexa_list_api, default_list_id, client_session

    try:
        # Load CLI settings
        with open(get_outputpath("cli_settings.json"), "r") as f:
            settings = CliSettings.model_validate_json(f.read())

            login_data_stored = read_from_file(get_outputpath("login_data.json"))

            client_session = ClientSession()

            password = keyring.get_password(
                KEYRING_SERVICE, f"{settings.email}-{PASSWORD_KEY}"
            )

            if not password:
                console.print(
                    f"[bold red]No password found in keyring for {settings.email}. Please run setup option first.[/bold red]"
                )
                sys.exit(1)

            amazon_echo_api = AmazonEchoApi(
                client_session=client_session,
                login_email=settings.email,
                login_password=password,
                login_data=login_data_stored,
            )

            try:
                await amazon_echo_api.login.login_mode_stored_data()
            except CannotAuthenticate:
                console.print(
                    f"[bold red]Cannot authenticate with {settings.email} credentials[/bold red]"
                )
                raise
            except CannotConnect:
                console.print(
                    f"[bold red]Cannot connect to {amazon_echo_api.domain} Amazon host[/bold red]"
                )
                raise
            except CannotRegisterDevice:
                console.print(
                    f"[bold red]Cannot register device for {settings.email}[/bold red]"
                )
                raise

        alexa_list_api = AlexaToDoAPI(amazon_echo_api)
        default_list_id = settings.default_list_id

    except AmazonError:
        console.print("[bold red]Login failed.[/bold red]")
        sys.exit(1)
    except FileNotFoundError:
        console.print(
            "CLI settings not found. Please run setup option first.", style="red"
        )
        sys.exit(1)

### Decorators for CLI commands ###

def with_alexa_api(func):
    """Decorator that initializes the Alexa API connection before function execution.

    Args:
        func: The async function to wrap.

    Returns:
        wrapper: The wrapped function that handles API initialization and cleanup.

    Example:
        @with_alexa_api
        async def my_function():
            # Function will have access to initialized alexa_list_api
            pass
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            with console.status("Logging into Alexa API..."):
                await init_api()
            return await func(*args, **kwargs)
        finally:
            if client_session:
                await client_session.close()

    return wrapper


def cli_command(func):
    """Decorator that wraps an async function to run in the asyncio event loop.

    Args:
        func: The async function to wrap.

    Returns:
        wrapper: The wrapped function that handles asyncio.run.

    Example:
        @cli_command
        async def my_function():
            # Function will run in asyncio event loop
            pass
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper

### CLI Commands ###

@app.command()
def setup():
    """Command to set up the Alexa Lists CLI with user credentials and preferences."""
    asyncio.run(setup_async())


async def setup_async():
    """Async implementation of the setup command.

    Guides the user through the setup process:
    1. Collects Amazon credentials and OTP secret
    2. Stores sensitive data in system keyring
    3. Authenticates with Amazon
    4. Lets user select default list
    5. Saves non-sensitive settings to file

    Raises:
        Exception: If any step of the setup process fails
    """
    try:
        # Welcome message
        console.print("[bold blue]Welcome to the Alexa Lists CLI Setup![/bold blue]")
        console.print("This will guide you through setting up your Alexa Lists CLI.")
        console.print(
            "You will need your Amazon account credentials and an OTP token for two-factor authentication.\n"
        )
        console.print(
            "The password will be stored securely in your system's keyring.\n"
        )

        while True:
            email = console.input("Enter your Amazon email: ").strip()
            if email and "@" in email and "." in email:
                break
            console.print(
                "[red]Invalid email format. Please enter a valid email address.[/red]"
            )

        while True:
            password = console.input("Enter your Amazon password: ", password=True)
            if password:  # Basic password length check
                break
            console.print("[red]Password cannot be empty.[/red]")

        # Store sensitive data in keyring
        keyring.set_password(KEYRING_SERVICE, f"{email}-{PASSWORD_KEY}", password)

        client_session = ClientSession()

        amazon_echo_api = AmazonEchoApi(
            client_session=client_session, login_email=email, login_password=password
        )

        while True:
            otp_token = console.input("Enter current OTP token: ")
            if len(otp_token) == 6:  # Basic OTP token length check
                break
            console.print("[red]OTP token must be 6 digits.[/red]")

        with console.status("[bold blue]Logging into Alexa API..."):
            try:
                login_data = await amazon_echo_api.login.login_mode_interactive(
                    otp_token
                )
            except CannotAuthenticate:
                console.print(
                    f"[bold red]Cannot authenticate with {email} credentials[/bold red]"
                )
                raise
            except CannotConnect:
                console.print(
                    f"[bold red]Cannot connect to {amazon_echo_api.domain} Amazon host[/bold red]"
                )
                raise
            except CannotRegisterDevice:
                console.print(
                    f"[bold red]Cannot register device for {email}[/bold red]"
                )
                raise

        with console.status("[bold blue]Saving login data to disk..."):
            save_to_file(login_data)

        console.print("[green]Logged in successfully![/green]")

        # Get available lists
        alexa_list_api = AlexaToDoAPI(amazon_echo_api)
        with console.status("[bold blue]Fetching available lists..."):
            lists = await alexa_list_api.get_lists()

        # Display lists and get user selection
        console.print("\n[bold]Available Lists:[/bold]")
        for i, list_info in enumerate(lists):
            console.print(f"  [{i}] {list_info.name}")

        while True:
            default_list_id = console.input(
                "\nWhich is your default list? Enter the number: "
            )
            if default_list_id.isdigit() and 0 <= int(default_list_id) < len(lists):
                default_list_id = lists[int(default_list_id)].id
                break
            console.print("[red]Invalid input. Please enter a valid list number.[/red]")

        # Save non-sensitive settings
        cli_settings = CliSettings(
            email=email,
            default_list_id=default_list_id,
        )

        settings_path = get_outputpath("cli_settings.json")
        cli_settings_json = cli_settings.model_dump_json(indent=4)
        with open(settings_path, "w") as f:
            f.write(cli_settings_json)

        console.print("[green]Settings and credentials saved successfully![/green]")

    except AmazonError:
        console.print("[bold red]Login failed.[/bold red]")
        sys.exit(1)
    except Exception:
        console.print("[bold red]Error during setup:[/bold red]")
        raise  # Typer will catch this and print the stack trace for debugging
    finally:
        if "alexa_login" in locals():
            await client_session.close()


@app.command()
@cli_command
@with_alexa_api
async def list(list_id: str = ""):
    """Fetch and display all items from a specified Alexa list.

    Args:
        list_id: The ID of the list to fetch items from.
            If not provided, uses the default list.
    """
    if not list_id:
        list_id = default_list_id

    with console.status("Fetching list items from Alexa API..."):
        list_items = await alexa_list_api.get_list_items(list_id)

    for list_item in list_items:
        line = typer.style(
            f"[{'x' if list_item.is_checked else ' '}] {list_item.name}",
            fg=typer.colors.GREEN if list_item.is_checked else typer.colors.RED,
        )
        typer.echo(line)


@app.command()
@cli_command
@with_alexa_api
async def check(item_name: str, list_id: str = ""):
    """Toggle the checked status of an item in a specified Alexa list.

    Args:
        item_name: The name of the item to toggle.
        list_id: The ID of the list containing the item.
            If not provided, uses the default list.

    Raises:
        ItemNotFoundException: If the item is not found in the list.
    """
    if not list_id:
        list_id = default_list_id

    try:
        with console.status("Fetching item from Alexa API and find item by name..."):
            item = await alexa_list_api.get_item_by_name(list_id, item_name)

        if item is None:
            console.print(f'Item "{item_name}" not found.', style="red")
            return

        with console.status("Toggling item status..."):
            await alexa_list_api.set_item_checked_status(
                list_id, item.id, not item.is_checked, item.version
            )

        console.print(f'Item "{item_name}" toggled sucessfully.', style="green")
    except ItemNotFoundException:
        console.print(f'Item "{item_name}" not found.', style="red")


@app.command()
@cli_command
@with_alexa_api
async def add(item_name: str, list_id: str = ""):
    """Add a new item to a specified Alexa list.

    Args:
        item_name: The name of the item to add.
        list_id: The ID of the list to add the item to.
            If not provided, uses the default list.
    """
    if not list_id:
        list_id = default_list_id

    with console.status("Adding item to list..."):
        await alexa_list_api.add_item(list_id, item_name)

    console.print(f'Item "{item_name}" added successfully.', style="green")


@app.command()
@cli_command
@with_alexa_api
async def remove(item_name: str, list_id: str = ""):
    """Remove an item from a specified Alexa list.

    Args:
        item_name: The name of the item to remove.
        list_id: The ID of the list to remove the item from.
            If not provided, uses the default list.

    Raises:
        ItemNotFoundException: If the item is not found in the list.
    """
    if not list_id:
        list_id = default_list_id

    try:
        with console.status("Fetching item from Alexa API and find item by name..."):
            item = await alexa_list_api.get_item_by_name(list_id, item_name)

        with console.status("Removing item from list..."):
            await alexa_list_api.delete_item(list_id, item.id, item.version)

        console.print(f'Item "{item_name}" removed successfully.', style="green")
    except ItemNotFoundException:
        console.print(f'Item "{item_name}" not found.', style="red")

@app.command()
@cli_command
@with_alexa_api
async def lists():
    """Fetch and display all available Alexa lists."""
    with console.status("Fetching available lists from Alexa API..."):
        lists = await alexa_list_api.get_lists()

    console.print("\n[bold]Available Lists:[/bold]")
    for list_info in lists:
        console.print(f"  - {list_info.name} (ID: {list_info.id})")

if __name__ == "__main__":
    app()