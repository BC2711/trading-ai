from datetime import datetime, timezone

from pydantic import BaseModel, Field


class EconomicCalendarEventCreate(BaseModel):
    event_name: str = Field(..., min_length=2, max_length=180)
    country: str = Field(..., min_length=2, max_length=80)
    impact_level: str = Field(..., pattern="^(low|medium|high)$")
    event_datetime: datetime
    affected_assets: list[str] = Field(default_factory=list)
    previous_value: str | None = None
    forecast_value: str | None = None
    actual_value: str | None = None


class EconomicCalendarEventRead(EconomicCalendarEventCreate):
    id: int
    trading_blackout_warning: str
    high_impact: bool
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EconomicCalendarResponse(BaseModel):
    events: list[EconomicCalendarEventRead] = Field(default_factory=list)
