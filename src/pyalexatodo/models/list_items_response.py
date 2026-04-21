from pydantic import BaseModel

from pyalexatodo.models.list_item import ListItem

class ListItemsResponse(BaseModel):
    """Response model for fetching items from an Alexa list."""
    itemInfoList: list[ListItem]