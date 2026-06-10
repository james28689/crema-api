from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ShotCreate(BaseModel):
    bean_id: UUID
    dose_g: float = Field(gt=0)
    yield_g: float = Field(gt=0)
    time_sec: int = Field(gt=0)
    grinder_setting: str | None = None
    rating: int = Field(ge=1, le=10)
    taste_tags: list[str] | None = None
    notes: str | None = None
    pulled_at: datetime | None = None


class BeanName(BaseModel):
    id: UUID
    name: str


class ShotResponse(BaseModel):
    id: UUID
    bean_id: UUID | None
    bean: BeanName | None
    dose_g: float
    yield_g: float
    ratio: float
    time_sec: int
    grinder_setting: str | None
    rating: int
    taste_tags: list[str] | None
    notes: str | None
    pulled_at: datetime
    days_off_roast_at_pull: int | None


class ShotListResponse(BaseModel):
    data: list[ShotResponse]
    next_cursor: UUID | None
