from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class AProfile(BaseModel):
    id: str
    public_id: Optional[str] = None
    service: str
    name: str
    indexed: datetime
    updated: datetime