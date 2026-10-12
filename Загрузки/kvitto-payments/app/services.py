SEED_TARIFFS: list[tuple[str, str, int]] = [
    ("basic", "Basic", 990_000),
    ("standard", "Standard", 1_990_000),
    ("premium", "Premium", 2_990_000),
]

PROMO_PERCENT: dict[str, int] = {"KVITTO10": 10}

INSTALLMENT_TERMS = (3, 6, 12)

ALLOWED_TRANSITIONS: set[tuple[str, str]] = {
    ("pending", "succeeded"),
    ("pending", "failed"),
    ("succeeded", "refunded"),
}


class UnknownPromoError(ValueError):
    pass


def calc_discount(price: int, promo_code: str | None) -> int:
    if promo_code is None:
        return 0
    percent = PROMO_PERCENT.get(promo_code.strip().upper())
    if percent is None:
        raise UnknownPromoError(promo_code)
    return price * percent // 100


def build_schedule(amount: int, months: int) -> list[int]:
    base, remainder = divmod(amount, months)
    return [base + 1 if i < remainder else base for i in range(months)]


def can_transition(current: str, new: str) -> bool:
    return (current, new) in ALLOWED_TRANSITIONS
