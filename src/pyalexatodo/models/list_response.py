from pyalexatodo.models.list_info import ListInfo


from pydantic import BaseModel


class ListResponse(BaseModel):
    """Response model for fetching Alexa shopping lists."""
    listInfoList: list[ListInfo]