from datetime import datetime, timedelta, timezone

from app.schemas.calendar import EconomicCalendarEventCreate, EconomicCalendarEventRead


_EVENTS: list[EconomicCalendarEventRead] = []
_NEXT_EVENT_ID = 1


def list_events(
    *,
    country: str | None = None,
    impact_level: str | None = None,
    asset: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[EconomicCalendarEventRead]:
    _ensure_defaults()
    events = list(_EVENTS)
    if country:
        events = [event for event in events if event.country.lower() == country.lower()]
    if impact_level:
        events = [event for event in events if event.impact_level == impact_level]
    if asset:
        asset_upper = asset.upper()
        events = [event for event in events if any(asset_upper in item.upper() for item in event.affected_assets)]
    if start:
        events = [event for event in events if event.event_datetime >= _as_aware(start)]
    if end:
        events = [event for event in events if event.event_datetime <= _as_aware(end)]
    return sorted(events, key=lambda event: event.event_datetime)


def high_impact_events() -> list[EconomicCalendarEventRead]:
    return [event for event in list_events() if event.high_impact]


def create_event(payload: EconomicCalendarEventCreate) -> EconomicCalendarEventRead:
    _ensure_defaults()
    event = _build_event(payload)
    _EVENTS.append(event)
    return event


def _ensure_defaults() -> None:
    if _EVENTS:
        return

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    defaults = [
        EconomicCalendarEventCreate(
            event_name="US CPI Inflation Rate",
            country="United States",
            impact_level="high",
            event_datetime=now + timedelta(hours=6),
            affected_assets=["USD", "BTCUSDT", "ETHUSDT", "SPX"],
            previous_value="3.4%",
            forecast_value="3.2%",
            actual_value=None,
        ),
        EconomicCalendarEventCreate(
            event_name="Federal Reserve Rate Decision",
            country="United States",
            impact_level="high",
            event_datetime=now + timedelta(days=1, hours=2),
            affected_assets=["USD", "BTCUSDT", "NASDAQ", "GOLD"],
            previous_value="5.25%",
            forecast_value="5.25%",
            actual_value=None,
        ),
        EconomicCalendarEventCreate(
            event_name="Euro Area Manufacturing PMI",
            country="Euro Area",
            impact_level="medium",
            event_datetime=now + timedelta(days=2),
            affected_assets=["EURUSD", "DAX", "EURO"],
            previous_value="47.3",
            forecast_value="48.1",
            actual_value=None,
        ),
        EconomicCalendarEventCreate(
            event_name="Japan Trade Balance",
            country="Japan",
            impact_level="low",
            event_datetime=now + timedelta(days=3, hours=4),
            affected_assets=["JPY", "USDJPY", "NIKKEI"],
            previous_value="-462B",
            forecast_value="-380B",
            actual_value=None,
        ),
        EconomicCalendarEventCreate(
            event_name="Crypto ETF Flow Report",
            country="Global",
            impact_level="medium",
            event_datetime=now + timedelta(hours=18),
            affected_assets=["BTCUSDT", "ETHUSDT"],
            previous_value="$420M",
            forecast_value="$500M",
            actual_value=None,
        ),
    ]
    for payload in defaults:
        _EVENTS.append(_build_event(payload))


def _build_event(payload: EconomicCalendarEventCreate) -> EconomicCalendarEventRead:
    global _NEXT_EVENT_ID
    event_datetime = _as_aware(payload.event_datetime)
    high_impact = payload.impact_level == "high"
    event = EconomicCalendarEventRead(
        id=_NEXT_EVENT_ID,
        event_name=payload.event_name,
        country=payload.country,
        impact_level=payload.impact_level,
        event_datetime=event_datetime,
        affected_assets=[asset.upper() for asset in payload.affected_assets],
        previous_value=payload.previous_value,
        forecast_value=payload.forecast_value,
        actual_value=payload.actual_value,
        trading_blackout_warning=_blackout_warning(payload.impact_level, event_datetime),
        high_impact=high_impact,
        created_at=datetime.now(timezone.utc),
    )
    _NEXT_EVENT_ID += 1
    return event


def _blackout_warning(impact_level: str, event_datetime: datetime) -> str:
    if impact_level == "high":
        return f"High-impact blackout: avoid new trades 30 minutes before and after {event_datetime.isoformat()}."
    if impact_level == "medium":
        return "Monitor spreads and reduce size around the release window."
    return "Low blackout risk; normal execution rules apply."


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
