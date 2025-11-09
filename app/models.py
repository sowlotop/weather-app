from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Boolean, DateTime, JSON, func, text
from datetime import datetime

class Base(DeclarativeBase):
    pass

class WeatherQuery(Base):
    __tablename__ = "weather_queries"
    id: Mapped[int] = mapped_column(primary_key=True)
    city: Mapped[str] = mapped_column(String(255), index=True)
    units: Mapped[str] = mapped_column(String(10))
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
