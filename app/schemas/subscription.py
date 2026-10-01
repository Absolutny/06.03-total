from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import SubscriptionType


class SubscriptionIssue(BaseModel):
    client_id: int = Field(gt=0)
    type: SubscriptionType
    duration_days: int = Field(default=30, gt=0, le=366)
    visits: int | None = Field(default=None, gt=0, le=1000)
    amount: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)

    @model_validator(mode="after")
    def _visits_for_single(self):
        if self.type == SubscriptionType.SINGLE and self.visits is None:
            self.visits = 1
        return self


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    type: SubscriptionType
    visits_left: int | None
    start_date: date
    end_date: date
    is_active: bool


class RevenueReport(BaseModel):
    date_from: date
    date_to: date
    total_revenue: Decimal
    payments_count: int
