from pydantic import BaseModel, Field

from pyalexatodo.models.list_item_status import ListItemStatus


class ListItem(BaseModel):
    """
    Represents an item in a list.
    Attributes:
        id: The unique identifier of the list item.
        status: The current status of the list item.
        original_name: The original name of the list item.
    Properties:
        name: Returns the name of the list item with the first letter capitalized.
        is_checked: Returns True if the list item is marked as complete, otherwise False.
    """

    id: str = Field(alias="itemId")  # Alias is used to map the JSON key to the attribute name
    status: ListItemStatus = Field(alias="itemStatus")
    original_name: str = Field(alias="itemName")
    version: int

    @property
    def name(self) -> str:
        """
        Get the name of the list item with the first letter capitalized.

        Returns:
            Name of the list item with the first letter capitalized.
        """
        return self.original_name[0].upper() + self.original_name[1:]

    @property
    def is_checked(self) -> bool:
        """
        Check if the list item is marked as complete.

        Returns:
            True if the list item is marked as complete, otherwise False.
        """
        return self.status == ListItemStatus.COMPLETE
