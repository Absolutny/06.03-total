from pydantic import BaseModel, ConfigDict, Field


class HallCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    capacity: int = Field(gt=0, le=1000)


class HallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    capacity: int
