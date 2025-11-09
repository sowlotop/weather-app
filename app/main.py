from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime
import io, csv, logging

from .config import settings
from .database import SessionLocal
from .models import WeatherQuery
from .schemas import WeatherOut, HistoryPage, HistoryItem
from .ratelimit import RateLimiter
from .weather_service import fetch_external, recent_cached, insert_query
from .logging_utils import configure_logging

logger = configure_logging()
app = FastAPI(title="Weather Query API")
limiter = RateLimiter(settings.RATE_LIMIT_PER_MINUTE)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.utcnow()
    ip = client_ip(request)
    logger.info(f"event=request_start ip={{ip}} method={{request.method}} path={{request.url.path}}")
    try:
        response = await call_next(request)
        code = response.status_code
    except Exception as e:
        logger.exception("event=error %s", e)
        raise
    finally:
        end = datetime.utcnow()
        dur_ms = int((end - start).total_seconds() * 1000)
        logger.info(f"event=request_end ip={{ip}} method={{request.method}} path={{request.url.path}} status={{code}} duration_ms={{dur_ms}}")
    return response

@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(select(func.count(WeatherQuery.id))).scalar()
        db_ok = True
    except Exception:
        db_ok = False
    return {"db": "ok" if db_ok else "fail"}

@app.post("/weather", response_model=WeatherOut)
async def get_weather(request: Request, city: str = Query(..., min_length=1), units: str = Query("metric", pattern="^(metric|imperial)$"), db: Session = Depends(get_db)):
    ip = client_ip(request)
    if not limiter.hit(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.")
    cached = recent_cached(db, city, units)
    if cached:
        row = insert_query(db, city, units, cached.raw_json, from_cache=True)
        return WeatherOut(city=row.city, units=row.units, temperature=row.temperature, description=row.description, from_cache=True, created_at=row.created_at)
    try:
        data = await fetch_external(city, units)
        logger.info("event=external_api_ok city=%s units=%s", city, units)
    except Exception as e:
        logger.error("event=external_api_error city=%s error=%s", city, e)
        raise HTTPException(status_code=502, detail="Upstream weather API error")
    row = insert_query(db, city, units, data, from_cache=False)
    return WeatherOut(city=row.city, units=row.units, temperature=row.temperature, description=row.description, from_cache=False, created_at=row.created_at)

@app.get("/history", response_model=HistoryPage)
def history(city: str | None = Query(None), from_: str | None = Query(None, alias="from"), to: str | None = Query(None), page: int = Query(1, ge=1), per_page: int = Query(10, ge=1, le=100), export: str | None = Query(None), db: Session = Depends(get_db)):
    q = select(WeatherQuery)
    if city:
        q = q.where(func.lower(WeatherQuery.city).like(f"%{city.lower()}%"))
    def parse_date(s: str | None):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None
    d_from = parse_date(from_)
    d_to = parse_date(to)
    if d_from:
        q = q.where(WeatherQuery.created_at >= d_from)
    if d_to:
        q = q.where(WeatherQuery.created_at <= d_to)
    total = db.execute(q.with_only_columns(func.count(WeatherQuery.id))).scalar() or 0
    q = q.order_by(WeatherQuery.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    rows = db.execute(q).scalars().all()
    items = [HistoryItem(id=r.id, city=r.city, units=r.units, temperature=r.temperature, description=r.description, from_cache=r.from_cache, created_at=r.created_at) for r in rows]
    if export == "csv":
        qcsv = select(WeatherQuery)
        if city:
            qcsv = qcsv.where(func.lower(WeatherQuery.city).like(f"%{city.lower()}%"))
        if d_from:
            qcsv = qcsv.where(WeatherQuery.created_at >= d_from)
        if d_to:
            qcsv = qcsv.where(WeatherQuery.created_at <= d_to)
        qcsv = qcsv.order_by(WeatherQuery.created_at.desc())
        allrows = db.execute(qcsv).scalars().all()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "city", "units", "temperature", "description", "from_cache", "created_at"])
        for r in allrows:
            writer.writerow([r.id, r.city, r.units, r.temperature, r.description, r.from_cache, r.created_at.isoformat()])
        buf.seek(0)
        headers = {"Content-Disposition": "attachment; filename=history.csv"}
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)
    return HistoryPage(page=page, per_page=per_page, total=total, items=items)
