from pydantic import BaseModel

class CliSettings(BaseModel):
    """
    Represents the CLI settings for Alexa Lists.
    """

    email: str
    default_list_id: str

