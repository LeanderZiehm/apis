from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    id: str
    original_name: str
    stored_name: str
    size: int


class RenameRequest(BaseModel):
    new_name: str = Field(
        ...,
        min_length=1,
        regex=r"^[a-zA-Z0-9._-]+$",
        description="Filename without extension",
    )
