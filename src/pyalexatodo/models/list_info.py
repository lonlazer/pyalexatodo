from pydantic import BaseModel, Field

from pyalexatodo.models.list_type import ListType


class ListInfo(BaseModel):
    """
    Represents information about a list.

    Attributes:
        list_id: The unique identifier for the list.
        list_type: The type of the list.
        custom_list_name: The name of the list, applicable only for CUSTOM lists.

    Properties:
        name: Returns the name of the list. If the list type is CUSTOM, it returns the custom list name.
                   Otherwise, it returns the capitalized value of the list type.
    """

    id: str = Field(alias="listId")  # Alias is used to map the JSON key to the attribute name
    list_type: ListType = Field(alias="listType")
    custom_list_name: str = Field(default="", alias="listName")

    @property
    def name(self):
        """
        Get the name of the list.

        If the list type is custom, return the custom list name.
        Otherwise, return the capitalized value of the list type.

        Returns:
            The name of the list.
        """
        if self.list_type == ListType.CUSTOM:
            return self.custom_list_name
        return self.list_type.value.capitalize()
