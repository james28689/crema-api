from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

BeanProcess = Literal["washed", "natural", "honey"]
BeanRoastLevel = Literal["light", "medium", "dark"]


class BeanCreate(BaseModel):
    name: str = Field(min_length=1)
    roaster: str | None = None
    origin: str | None = None
    process: BeanProcess | None = None
    roast_level: BeanRoastLevel | None = None
    roast_date: date | None = None


class BeanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    roaster: str | None = None
    origin: str | None = None
    process: BeanProcess | None = None
    roast_level: BeanRoastLevel | None = None
    roast_date: date | None = None
    is_active: bool | None = None


class BeanResponse(BaseModel):
    id: UUID
    name: str
    roaster: str | None
    origin: str | None
    process: BeanProcess | None
    roast_level: BeanRoastLevel | None
    roast_date: date | None
    days_off_roast: int | None
    is_active: bool
    shot_count: int
    created_at: datetime
