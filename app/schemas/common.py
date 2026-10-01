from datetime import datetime

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: int
    code: str
    message: str
    timestamp: datetime
    details: dict[str, str] | None = None
