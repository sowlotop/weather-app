import httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .config import settings
from .models import WeatherQuery

async def fetch_external(city: str, units: str) -> dict:
    params = {"q": city, "appid": settings.OPENWEATHER_API_KEY, "units": units}
    timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(settings.EXTERNAL_API_BASE, params=params)
        r.raise_for_status()
        return r.json()

def parse_weather(data: dict) -> tuple[float | None, str | None]:
    temp = None
    desc = None
    try:
        temp = float(data.get("main", {}).get("temp"))
    except Exception:
        temp = None
    try:
        desc = data.get("weather", [{}])[0].get("description")
    except Exception:
        desc = None
    return temp, desc

def recent_cached(db: Session, city: str, units: str) -> WeatherQuery | None:
    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    stmt = (
        select(WeatherQuery)
        .where(func.lower(WeatherQuery.city) == city.lower())
        .where(WeatherQuery.units == units)
        .where(WeatherQuery.created_at >= five_min_ago)
        .order_by(WeatherQuery.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()

def insert_query(db: Session, city: str, units: str, data: dict, from_cache: bool) -> WeatherQuery:
    temp, desc = parse_weather(data)
    row = WeatherQuery(city=city, units=units, temperature=temp, description=desc, raw_json=data, from_cache=from_cache)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
