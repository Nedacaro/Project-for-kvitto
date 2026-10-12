from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, model_validator

from app.services import INSTALLMENT_TERMS

PaymentMethod = Literal["card", "sbp", "installment"]
PaymentStatus = Literal["pending", "succeeded", "failed", "refunded"]


class TariffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    price: int


class PaymentCreate(BaseModel):
    tariff_id: str
    email: EmailStr
    method: PaymentMethod
    installment_months: int | None = None
    promo_code: str | None = None

    @model_validator(mode="after")
    def check_installment(self) -> "PaymentCreate":
        if self.method == "installment":
            if self.installment_months not in INSTALLMENT_TERMS:
                raise ValueError("installment_months must be 3, 6 or 12 for installment")
        else:
            self.installment_months = None
        return self


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: PaymentStatus
    tariff_id: str
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None
    schedule: list[int] | None
    email: EmailStr
    created_at: datetime


class BankWebhook(BaseModel):
    payment_id: int
    status: PaymentStatus
