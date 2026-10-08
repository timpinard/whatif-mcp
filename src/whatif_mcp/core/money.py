from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
HALF_CENT = 0.005


def round_money(value: float) -> float:
    cents = Decimal(repr(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    return float(cents) if cents != 0 else 0.0


def rounds_to_zero_or_below(value: float) -> bool:
    # Same answer as round_money(value) <= 0, without Decimal's precision limit on huge values.
    return value < HALF_CENT
