from whatif_mcp.core.errors import RuleError
from whatif_mcp.core.model import Account, AccountKind

MIN_GROWTH_RATE = -1.0
MAX_GROWTH_RATE = 1.0
MIN_VOLATILITY = 0.0
MAX_VOLATILITY = 1.0


def check_account(account: Account) -> None:
    if account.kind is AccountKind.LIABILITY and account.balance < 0:
        raise RuleError(
            f"balance {account.balance:g} is negative: a liability balance is the amount owed, "
            "never negative. Give the amount owed as a positive number."
        )
    if not MIN_GROWTH_RATE < account.growth_rate <= MAX_GROWTH_RATE:
        raise RuleError(
            f"growth_rate {account.growth_rate:g} is out of range: give a decimal greater than "
            f"{MIN_GROWTH_RATE:g} and at most {MAX_GROWTH_RATE:g} (0.07 means 7%)."
        )
    if not MIN_VOLATILITY <= account.volatility <= MAX_VOLATILITY:
        raise RuleError(
            f"volatility {account.volatility:g} is out of range: give a decimal from "
            f"{MIN_VOLATILITY:g} to {MAX_VOLATILITY:g} (0.15 means 15%)."
        )
