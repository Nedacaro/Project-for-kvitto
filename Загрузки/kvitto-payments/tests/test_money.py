"""тесты чистой логики"""
import pytest

from app import services


def test_discount_without_promo_is_zero():
    assert services.calc_discount(1_990_000, None) == 0


@pytest.mark.parametrize("code", ["KVITTO10", "kvitto10", "Kvitto10"])
def test_discount_ten_percent_any_case(code):
    assert services.calc_discount(1_990_000, code) == 199_000


def test_unknown_promo_raises():
    with pytest.raises(services.UnknownPromoError):
        services.calc_discount(1_990_000, "NOPE")


@pytest.mark.parametrize("amount", [1_990_000, 1_791_000, 990_001, 7])
@pytest.mark.parametrize("months", [3, 6, 12])
def test_schedule_sum_equals_amount(amount, months):
    schedule = services.build_schedule(amount, months)
    assert len(schedule) == months
    assert sum(schedule) == amount
    assert max(schedule) - min(schedule) <= 1
    assert schedule == sorted(schedule, reverse=True)


def test_schedule_example_from_task():
    assert services.build_schedule(1_990_000, 3) == [663_334, 663_333, 663_333]
