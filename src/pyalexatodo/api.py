from http import HTTPMethod
from typing import TYPE_CHECKING

from aioamazondevices.api import AmazonEchoApi

from pyalexatodo.exceptions import ItemNotFoundException
from pyalexatodo.models.list_info import ListInfo
from pyalexatodo.models.list_response import ListResponse
from pyalexatodo.models.list_item_status import ListItemStatus
from pyalexatodo.models.list_items_response import ListItem, ListItemsResponse

if TYPE_CHECKING:
    from aiohttp import ClientResponse


class AlexaToDoAPI:
    """A client for interacting with Amazon Alexa shopping lists.

    This class provides methods to manage Alexa shopping lists, including:
    - Fetching lists and list items
    - Adding, removing, and updating items
    - Managing item status (checked/unchecked)

    All methods are asynchronous and require an active AmazonEchoApi login session.
    """
    def __init__(self, alexa_echo_api: AmazonEchoApi, base_url: str | None = None):
        """Initialize the Alexa List API client.

        Args:
            alexa_echo_api: An authenticated AmazonEchoApi instance.
            base_url: Base URL for API requests (for testing). If None, uses Amazon's URL.
        """
        self.alexa_echo_api = alexa_echo_api
        """AmazonEchoAPI instance used for making authenticated requests to the Alexa API."""

        self._domain_extension = alexa_echo_api.domain
        self._base_url = base_url or f"https://www.amazon.{self._domain_extension}"

    async def _http_request(
        self, method: HTTPMethod, url: str, data: dict
    ) -> "ClientResponse":
        """
        Make an HTTP request to the Alexa API.

        Args:
            method: The HTTP method to use (GET, POST, PUT, DELETE, etc.).
            url: The URL endpoint to request.
            data: The request data to be sent as JSON.

        Returns:
            The response object from the HTTP request.
        """
        _, response = await self.alexa_echo_api._http_wrapper.session_request(
            method=method, url=url, input_data=data, json_data=True,
        )

        return response

    async def get_lists(self) -> ListInfo[ListInfo]:
        """Fetch all available Alexa shopping lists.

        Returns:
            A list of shopping list information objects.

        Raises:
            Exception: If the API request fails.
        """
        result = await self._http_request(
            HTTPMethod.POST,
            f"{self._base_url}/alexashoppinglists/api/v2/lists/fetch",
            {},
        )

        if not result or result.status != 200:
            raise Exception("Failed to fetch lists")

        result_json = await result.json()
        list_infos = ListResponse(**result_json)

        return list_infos.listInfoList

    async def get_list_items(self, list_id: str) -> ListInfo[ListItem]:
        """Fetch all items from a specified Alexa shopping list.

        Args:
            list_id: The ID of the list to fetch items from.

        Returns:
            A list of shopping list items.

        Raises:
            Exception: If the API request fails.
        """
        result = await self._http_request(
            HTTPMethod.POST,
            f"{self._base_url}/alexashoppinglists/api/v2/lists/{list_id}/items/fetch?limit=100",
            {},
        )

        if not result or result.status != 200:
            raise Exception(f"Failed to fetch list items for list: {list_id}")

        result_json = await result.json()
        list_items = ListItemsResponse(**result_json)

        return list_items.itemInfoList

    async def set_item_checked_status(
        self, list_id: str, item_id: str, checked: bool, version: int
    ):
        """Update the checked status of an item in a shopping list.

        Args:
            list_id: The ID of the list containing the item.
            item_id: The ID of the item to update.
            checked: True to mark as complete, False to mark as active.
            version: The current version of the item.
                     The value is included in the get_list_items response and is required by the Amazon API.

        Raises:
            Exception: If the API request fails.
        """
        result = await self._http_request(
            HTTPMethod.PUT,
            f"{self._base_url}/alexashoppinglists/api/v2/lists/{list_id}/items/{item_id}?version={version}",
            {
                "itemAttributesToUpdate": [
                    {
                        "type": "itemStatus",
                        "value": ListItemStatus.COMPLETE.value
                        if checked
                        else ListItemStatus.ACTIVE.value,
                    }
                ],
                "itemAttributesToRemove": [],
            },
        )

        if not result or result.status != 200:
            raise Exception(f"Failed to toggle item: {item_id}")

    async def add_item(self, list_id: str, name: str):
        """Add a new item to a shopping list.

        Args:
            list_id: The ID of the list to add the item to.
            name: The name of the item to add.

        Raises:
            Exception: If the API request fails.
        """
        result = await self._http_request(
            HTTPMethod.POST,
            f"{self._base_url}/alexashoppinglists/api/v2/lists/{list_id}/items",
            {
                "items": [
                    {
                        "itemType": "KEYWORD",
                        "itemName": name,
                    }
                ]
            },
        )

        if not result or result.status != 200:
            raise Exception(f"Failed to add item: {name}")

    async def delete_item(self, list_id: str, item_id: str, version: int):
        """Delete an item from a shopping list.

        Args:
            list_id: The ID of the list containing the item.
            item_id: The ID of the item to delete.
            version: The current version of the item.
                     The value is included in the get_list_items response and is required by the Amazon API.

        Raises:
            Exception: If the API request fails.
        """
        result = await self._http_request(
            HTTPMethod.DELETE,
            f"{self._base_url}/alexashoppinglists/api/v2/lists/{list_id}/items/{item_id}?version={version}",
            {},
        )

        if not result or result.status != 200:
            raise Exception(f"Failed to delete item: {item_id}")

    async def rename_item(
        self, list_id: str, item_id: str, new_name: str, version: int
    ):
        """Rename an item in a shopping list.

        Args:
            list_id: The ID of the list containing the item.
            item_id: The ID of the item to rename.
            new_name: The new name for the item.
            version: The current version of the item.
                     The value is included in the get_list_items response and is required by the Amazon API.

        Raises:
            Exception: If the API request fails.
        """
        result = await self._http_request(
            HTTPMethod.PUT,
            f"{self._base_url}/alexashoppinglists/api/v2/lists/{list_id}/items/{item_id}?version={version}",
            {
                "itemAttributesToUpdate": [{"type": "itemName", "value": new_name}],
                "itemAttributesToRemove": [],
            },
        )

        if not result or result.status != 200:
            raise Exception(f"Failed to rename item: {item_id}")

    async def get_item_by_name(self, list_id: str, name: str) -> ListItem:
        """Find an item in a shopping list by its name.

        The search is case-insensitive. If multiple items have the same name,
        the first one found will be returned.

        Args:
            list_id: The ID of the list to search in.
            name: The name of the item to find.

        Returns:
            The found item.

        Raises:
            ItemNotFoundException: If no item with the given name is found.
        """
        list_items = await self.get_list_items(list_id)
        for list_item in list_items:
            if list_item.name.casefold() == name.casefold():
                return list_item
        raise ItemNotFoundException
