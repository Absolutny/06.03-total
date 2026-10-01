from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import BookingStatus


class BookingCreate(BaseModel):
    schedule_slot_id: int = Field(gt=0)


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    schedule_slot_id: int
    status: BookingStatus
    created_at: datetime


class AttendanceRequest(BaseModel):
    attended: bool = True
