from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import security, services
from app.database import SessionLocal, get_db
from app.models import Payment, Tariff
from app.schemas import BankWebhook, PaymentCreate, PaymentOut, PaymentStatus, TariffOut


def seed_tariffs(db: Session) -> None:
    for tariff_id, title, price in services.SEED_TARIFFS:
        if db.get(Tariff, tariff_id) is None:
            db.add(Tariff(id=tariff_id, title=title, price=price))
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with SessionLocal() as db:
        seed_tariffs(db)
    yield


app = FastAPI(title="Kvitto payments", lifespan=lifespan)


@app.get("/tariffs", response_model=list[TariffOut])
def list_tariffs(db: Session = Depends(get_db)):
    return db.scalars(select(Tariff).order_by(Tariff.price)).all()


def _find_by_key(db: Session, key: str) -> Payment | None:
    return db.scalar(select(Payment).where(Payment.idempotency_key == key))


@app.post("/payments", response_model=PaymentOut, status_code=201)
def create_payment(
    data: PaymentCreate,
    response: Response,
    db: Session = Depends(get_db),
    
    idempotency_key: str | None = Header(default=None),
):
    if idempotency_key:
        existing = _find_by_key(db, idempotency_key)
        if existing:
            response.status_code = 200
            return existing

    tariff = db.get(Tariff, data.tariff_id)
    if tariff is None:
        raise HTTPException(status_code=404, detail="Tariff not found")

    try:
        discount = services.calc_discount(tariff.price, data.promo_code)
    except services.UnknownPromoError:
        raise HTTPException(status_code=422, detail="Unknown promo code")
    amount = tariff.price - discount

    schedule = None
    if data.method == "installment":
        assert data.installment_months is not None  
        schedule = services.build_schedule(amount, data.installment_months)

    payment = Payment(
        status="pending",
        tariff_id=tariff.id,
        amount=amount,
        discount=discount,
        method=data.method,
        installment_months=data.installment_months,
        schedule=schedule,
        email=data.email,
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing = _find_by_key(db, idempotency_key)
            if existing:
                response.status_code = 200
                return existing
        raise
    return payment


@app.get("/payments", response_model=list[PaymentOut])
def list_payments(
    email: str | None = None,
    status: PaymentStatus | None = None,
    db: Session = Depends(get_db),
):
    query = select(Payment).order_by(Payment.id)
    if email is not None:
        query = query.where(func.lower(Payment.email) == email.strip().lower())
    if status is not None:
        query = query.where(Payment.status == status)
    return db.scalars(query).all()


@app.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


async def verify_webhook_signature(
    request: Request,
    x_signature: str | None = Header(default=None),
) -> None:
    secret = security.webhook_secret()
    if secret is None:
        return
    raw_body = await request.body()  
    if not security.verify_signature(secret, raw_body, x_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


@app.post("/webhooks/bank", dependencies=[Depends(verify_webhook_signature)])
def bank_webhook(data: BankWebhook, db: Session = Depends(get_db)):
    payment = db.get(Payment, data.payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    if not services.can_transition(payment.status, data.status):
        return JSONResponse(status_code=409, content={"error": "invalid_transition"})

    payment.status = data.status
    db.commit()
    return {"result": "ok"}
