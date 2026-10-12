from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[str] = mapped_column(String, primary_key=True)  
    title: Mapped[str] = mapped_column(String)
    price: Mapped[int] = mapped_column(Integer)  # копейки


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    tariff_id: Mapped[str] = mapped_column(ForeignKey("tariffs.id"))
    amount: Mapped[int] = mapped_column(Integer)  # к оплате, копейки
    discount: Mapped[int] = mapped_column(Integer, default=0)  # скидка, копейки
    method: Mapped[str] = mapped_column(String)
    installment_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    email: Mapped[str] = mapped_column(String)
   # идемпотентность:
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
