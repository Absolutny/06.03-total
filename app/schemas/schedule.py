from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class SlotCreate(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    trainer_id: int = Field(gt=0)
    hall_id: int = Field(gt=0)
    start_time: datetime
    end_time: datetime
    max_clients: int = Field(gt=0, le=1000)
    price: Decimal = Field(default=Decimal("0"), ge=0, le=1_000_000, decimal_places=2)

    @field_validator("start_time", "end_time")
    @classmethod
    def _naive(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            raise ValueError("Укажите местное время комплекса без часового пояса, например 2026-10-05T18:00:00")
        return v

    @model_validator(mode="after")
    def _check_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("Время окончания должно быть позже начала")
        return self


class SlotResponse(BaseModel):
    id: int
    title: str
    trainer_id: int
    trainer_name: str
    hall_id: int
    hall_name: str
    start_time: datetime
    end_time: datetime
    max_clients: int
    booked: int
    free_places: int
    price: Decimal
