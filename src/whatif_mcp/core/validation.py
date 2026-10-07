import json
import math
import re
from datetime import date

from whatif_mcp.core.errors import ValidationError
from whatif_mcp.core.model import Account, AccountKind, Flow, Frequency

MIN_GROWTH_RATE = -1.0
MAX_GROWTH_RATE = 1.0
MIN_VOLATILITY = 0.0
MAX_VOLATILITY = 1.0
MIN_INFLATION_RATE = -1.0
MAX_INFLATION_RATE = 1.0
MAX_FLOW_RATE = 1.0
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
DATE_PROBLEM = "is not a YYYY-MM-DD date"


def check_account(account: Account) -> None:
    if account.kind is AccountKind.LIABILITY and account.balance < 0:
        raise ValidationError(
            f"balance {account.balance:g} is negative: a liability balance is the amount owed, "
            "never negative. Give the amount owed as a positive number."
        )
    if not MIN_GROWTH_RATE < account.growth_rate <= MAX_GROWTH_RATE:
        raise ValidationError(
            f"growth_rate {account.growth_rate:g} is out of range: give a decimal greater than "
            f"{MIN_GROWTH_RATE:g} and at most {MAX_GROWTH_RATE:g} (0.07 means 7%)."
        )
    if not MIN_VOLATILITY <= account.volatility <= MAX_VOLATILITY:
        raise ValidationError(
            f"volatility {account.volatility:g} is out of range: give a decimal from "
            f"{MIN_VOLATILITY:g} to {MAX_VOLATILITY:g} (0.15 means 15%)."
        )


def check_flow(flow: Flow) -> None:
    if flow.from_account is None and flow.to_account is None:
        raise ValidationError(
            "from and to are both outside: a flow needs at least one account. "
            "Give from, to or both."
        )
    if flow.from_account == flow.to_account:
        raise ValidationError(
            f'to "{flow.to_account}" is the same account as from: give two different accounts, '
            "or leave one side out for money from or to outside."
        )
    if flow.amount is not None and flow.rate is not None:
        raise ValidationError(
            "amount and rate are both given: a flow is either a fixed amount or a rate of "
            "the rate_of account's balance. Give one."
        )
    if flow.rate_of is not None and flow.rate is None:
        raise ValidationError("rate is required with rate_of: give the rate as a decimal.")
    if flow.amount is None:
        _check_rate(flow)
    elif flow.amount <= 0:
        raise ValidationError(
            f"amount {flow.amount:g} is not above 0: give the amount moved each time as a "
            "positive number."
        )
    if flow.end_date is not None and flow.end_date < flow.start_date:
        raise ValidationError(
            f"end_date {flow.end_date.isoformat()} is before start_date "
            f"{flow.start_date.isoformat()}: give an end_date on or after the start_date."
        )


def _check_rate(flow: Flow) -> None:
    if flow.rate is None:
        raise ValidationError(
            "amount or rate is required: give a fixed amount, or a rate with rate_of."
        )
    if flow.rate_of is None:
        raise ValidationError(
            "rate_of is required with rate: name the account whose balance the rate applies to."
        )
    if not 0 < flow.rate <= MAX_FLOW_RATE:
        raise ValidationError(
            f"rate {flow.rate:g} is out of range: give a decimal above 0 and at most "
            f"{MAX_FLOW_RATE:g} (0.04 means 4% a year)."
        )


def check_fires(flow: Flow, today: date) -> None:
    if flow.frequency is Frequency.ONE_TIME and flow.start_date <= today:
        raise ValidationError(
            f"start_date {flow.start_date.isoformat()} is not after today "
            f"({today.isoformat()}): a one_time flow on or before today would never fire. "
            "Give a later start_date."
        )


def check_inflation_rate(rate: float) -> None:
    if not MIN_INFLATION_RATE < rate < MAX_INFLATION_RATE:
        raise ValidationError(
            f"{rate:g} is out of range: give a decimal greater than {MIN_INFLATION_RATE:g} and "
            f"less than {MAX_INFLATION_RATE:g} (0.03 means 3%)"
        )


def finite_number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValidationError("is not a number")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValidationError("is too large to be a number") from error
    if not math.isfinite(number):
        raise ValidationError(f"is {json.dumps(number)}, not a finite number")
    return number


def parse_date(text: str) -> date:
    if DATE_PATTERN.fullmatch(text) is None:
        raise ValidationError(DATE_PROBLEM)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise ValidationError(DATE_PROBLEM) from error
