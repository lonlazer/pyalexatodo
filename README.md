# pyalexatodo
[![Publish to PyPI](https://github.com/lonlazer/pyalexatodo/workflows/Publish%20to%20PyPI/badge.svg)](https://github.com/lonlazer/pyalexatodo/actions?query=workflow:"Publish+to+PyPI")
![GitHub branch check runs](https://img.shields.io/github/check-runs/lonlazer/pyalexatodo/main)
[![GitHub release](https://img.shields.io/github/release/lonlazer/pyalexatodo?include_prereleases=&sort=semver&color=blue)](https://github.com/lonlazer/pyalexatodo/releases/)
[![License](https://img.shields.io/badge/License-GPLv3-blue)](#license)
[![issues - pyalexatodo](https://img.shields.io/github/issues/lonlazer/pyalexatodo)](https://github.com/lonlazer/pyalexatodo/issues)
[![ruff](https://img.shields.io/badge/code_style-ruff-black
)](https://docs.astral.sh/ruff/)
[![Go to Python website](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Flonlazer%2Fpyalexatodo%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&query=project.requires-python&label=python&logo=python&logoColor=white)](https://python.org)


An unofficial Python library (and optional CLI) for Alexa to-do and shopping lists.
API reverse-engineered by intercepting the Alexa mobile app's HTTP traffic.

__Disclaimer__: This is an unofficial integration and is not created, endorsed, or supported by Amazon.

## Features

- Fetch lists and items (To-Do, Shopping, Custom)
- Add, remove, rename, and toggle items
- Optional CLI interface
- Asynchronous API for integration into other applications

## Installation

Install from PyPI:

```bash
pip install pyalexatodo
```

For CLI usage with additional dependencies:

```bash
pip install "pyalexatodo[cli]"
```

## CLI Usage

### Setup

First, set up your Amazon credentials:

```bash
pyalexatodo setup
```

### Commands

```
 pyalexatodo --help


 Usage: pyalexatodo [OPTIONS] COMMAND [ARGS]...

╭─ Commands ─────────────────────────────────────────────────────────────────────────────╮
│ setup   Command to set up the Alexa Lists CLI with user credentials and preferences.   │
│ list    Fetch and display all items from a specified Alexa list.                       │
│ check   Toggle the checked status of an item in a specified Alexa list.                │
│ add     Add a new item to a specified Alexa list.                                      │
│ remove  Remove an item from a specified Alexa list.                                    │
│ lists   Fetch and display all available Alexa lists.                                   │
╰────────────────────────────────────────────────────────────────────────────────────────╯
```

## Library Usage & API Documentation
See the [API documentation](https://lonlazer.github.io/pyalexatodo/pyalexatodo/api.html) for detailed method descriptions.

For are in-depth example including storing of the session information have a look on the [cli.py](src/pyalexatodo/cli.py).
### Minmal example
```python
import asyncio
from aiohttp import ClientSession
from aioamazondevices.api import AmazonEchoApi
from pyalexatodo.api import AlexaToDoAPI

async def main():
    async with ClientSession() as session:
        # Authenticate with Amazon
        amazon_api = AmazonEchoApi(
            client_session=session,
            login_email="your-email@example.com",
            login_password=input("Enter Password: ")
        )
        await amazon_api.login.login_mode_interactive(input("Enter 2FA code: "))

        # Create To-Do API client
        todo_api = AlexaToDoAPI(amazon_api)

        # Get lists
        lists = await todo_api.get_lists()
        print(f"Available lists: {[list.name for list in lists]}")

        # Add an item
        await todo_api.add_item(lists[0].id, "Buy boba")

        # Get items
        items = await todo_api.get_list_items(lists[0].id)
        print(f"Items: {[i.name for i in items]}")

asyncio.run(main())
```

## Development

### Setup

```bash
git clone https://github.com/lonlazer/pyalexatodo.git
cd pyalexatodo
uv sync
```

### Testing

```bash
uv run pytest
```

### Building

```bash
uv build
```

## Contributing

Contributions are welcome! Please follow the conventional commit format prepended by a [Gitmoji](https://gitmoji.dev/) for commit messages.
Make sure everything is formatted using ruff and pytest, ty, ruff checks are passing.

## Credits
- [aioamazondevices](https://github.com/chemelli74/aioamazondevices): This library is used for logging in and making authentified API calls to Amazon.

## License
This project is licenced under [GNU GENERAL PUBLIC LICENSE Version 3](LICENSE).
