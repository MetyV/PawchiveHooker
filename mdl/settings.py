from pydantic import BaseModel, Field

class Settings(BaseModel):
    semaphore: int = Field(default=4)
    auto_update: bool = Field(default=False)