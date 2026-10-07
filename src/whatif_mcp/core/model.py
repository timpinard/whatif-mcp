from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from whatif_mcp.core.errors import ValidationError

DEFAULT_INFLATION_RATE = 0.03


class AccountKind(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"


class Frequency(StrEnum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"
    ONE_TIME = "one_time"


@dataclass(frozen=True)
class Account:
    name: str
    kind: AccountKind
    balance: float
    balance_as_of: date
    growth_rate: float = 0.0
    volatility: float = 0.0


@dataclass(frozen=True)
class Flow:
    name: str
    from_account: str | None
    to_account: str | None
    amount: float | None
    rate: float | None
    rate_of: str | None
    frequency: Frequency
    start_date: date
    end_date: date | None = None


@dataclass(frozen=True)
class Model:
    accounts: tuple[Account, ...] = ()
    flows: tuple[Flow, ...] = ()
    inflation_rate: float = DEFAULT_INFLATION_RATE


def rate_terms(flow: Flow) -> tuple[float, str]:
    if flow.rate is None or flow.rate_of is None:
        raise ValidationError(f'flow "{flow.name}" is not a rate flow: it has no rate and rate_of.')
    return flow.rate, flow.rate_of
