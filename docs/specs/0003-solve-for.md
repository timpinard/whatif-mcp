# Spec 0003: Solve-for
- Status: draft
- Owner: Timothy Pinard
- Links: ADR 0001, ADR 0002, ADR 0003, ADR 0004 (all accepted). Depends on Spec 0002 (each trial
  is a what-if with one change) and through it on Spec 0001.

## Intent (why)
Many questions run backwards: "how much a month do I need to save to have $30,000 by June 2029?"
or "how much less can I spend and still have $4,000 left?". The assistant should not guess by
trying amounts one what-if at a time. `solve_for` varies the fixed amount of one named flow and
finds the amount that makes a target reach a given value by a date, or says plainly why no amount
does. Nothing is saved.

## Users and scenarios
One person, on their own machine, talking to an MCP client, with a model already built (Spec 0001).

1. "How much a month into savings to have $6,000 by next October?" -> target an account balance.
2. "How much can I spend on groceries and still have $4,000 of net worth then?" -> target net
   worth, lever a spending flow.
3. "What car payment clears the loan by next October?" -> target a liability balance of 0.
4. "I'm already on track, am I over-saving?" -> a required amount below the current one.
5. Any of the above with the target "in today's money".

## Requirements
| ID | Requirement (behavior, not implementation) |
|----|--------------------------------------------|
| R1 | `solve_for` takes `target` (number), `by_date`, `flow` (the name of a fixed-amount flow) and optionally `account` (omitted means net worth) and `in_todays_money`. The measurement for an amount is the target account's balance (or net worth) after all events of by_date, in a projection per Spec 0001 of a copy of the model in which only that flow's amount is changed, as a Spec 0002 `set_flow` change would. With `in_todays_money`, the measurement is deflated to today's money per Spec 0001 R15 before comparison. |
| R2 | It looks for an amount per occurrence between 0 and 1,000,000,000 whose measurement is within the tolerance max(0.001 x abs(target), 0.01) of the target. It does not assume whether raising the amount raises or lowers the measurement. |
| R3 | When found, it returns solved true, the flow, its frequency, the required amount, the current amount, the change (required minus current), what the target reaches at the required amount, and the target echoed (amount, account name or "net worth", by_date, nominal or today's money). A required amount below the current one is reported as a negative change. |
| R4 | When no amount qualifies, it returns solved false with a reason, the measurement at amount 0 (at_zero) and at the current amount (at_current), and the target echoed. Reasons: `flow_does_not_affect_target` when the measurement at 0 and at 1,000,000,000 are equal to the cent; `even_at_zero` when the target lies beyond the measurement at 0 on the side away from the measurement at 1,000,000,000 (only a negative amount would do); `even_at_maximum` when the target lies beyond the measurement at 1,000,000,000; `did_not_converge` when the target lies between them but the search's step limit ran out before the tolerance was met. A result is never solved true with a measurement outside the tolerance. |
| R5 | When a range of amounts all reach the target within tolerance, because the measurement stops changing (a liability paid off and capped at zero), the required amount is the smallest such amount, to the cent. (Open question 1.) |
| R6 | Invalid input is a tool error per Spec 0001 R16: a rate flow (only fixed-amount flows can be solved), an unknown flow or account name (listing the existing names), a by_date that is not after today or is more than 50 years after today, a model with no accounts, and wrong argument types. |
| R7 | `solve_for` never writes the model file; every result has `persisted: false`. |

## Acceptance criteria (each maps to 1+ test, in tests/test_0003_*.py)
Fixed today in every criterion: 2026-10-06. Money is compared to the cent unless a tolerance is
given. "File unchanged" means the model file's bytes and modification time are identical before
and after. Named models:

- Model S: Checking (asset, 10000), Savings (asset, 0); flows in this order: Contribution
  (Checking -> Savings, 100, monthly, start 2026-11-01), Groceries (from Checking, 700, monthly,
  start 2026-11-01). By 2027-10-01 each has fired 12 times.
- Model L: Checking (asset, 20000), Car loan (liability, 10000, growth_rate 0.06, an APR); Car
  payment (Checking -> Car loan, 500, monthly, start 2026-11-01).

| ID | Given / When / Then | Covers | Level | Test name |
|----|---------------------|--------|-------|-----------|
| AC1 | Given Model S, when `solve_for(target=6000, account="Savings", by_date="2027-10-01", flow="Contribution")` is called, then solved is true, frequency "monthly", current_amount 100.00, required_amount within 0.50 of 500.00 (6000 / 12), change equals required_amount - 100.00, reaches within 6.00 of 6000, and target {amount 6000, of "Savings", by_date "2027-10-01", values "nominal"}. | R1, R2, R3 | integration | test_AC1_solve_lands_on_target |
| AC2 | Given Model S, when solving Savings to 600 by 2027-10-01 with Contribution, then required_amount is within 0.50 of 50.00 and change is negative; when solving Savings to 0, then required_amount is 0.00 and change -100.00. | R2, R3 | unit | test_AC2_ahead_of_goal_reads_as_reduction |
| AC3 | Given Model S, when solving net worth (no account) to 4000 by 2027-10-01 with Groceries, then required_amount is within 0.50 of 500.00 ((10000 - 4000) / 12), below the current 700.00, and the target's `of` is "net worth". | R1, R2, R3 | unit | test_AC3_net_worth_target_with_spending_flow |
| AC4 | Given Model S, when solving Savings to 5500 by 2027-09-30 with Contribution, then required_amount is within 0.50 of 500.00 (11 occurrences up to the end of by_date, not of its month). | R1 | unit | test_AC4_target_measured_at_end_of_by_date |
| AC5 | Given Model S, when solving Savings to 1000000000000 by 2027-10-01 with Contribution, then solved is false, reason "even_at_maximum", at_zero 0.00, at_current 1200.00. | R4 | unit | test_AC5_unreachable_even_at_maximum |
| AC6 | Given Model S, when solving net worth to 20000 by 2027-10-01 with Groceries, then solved is false, reason "even_at_zero", at_zero 10000.00, at_current 1600.00. | R4 | unit | test_AC6_unreachable_even_at_zero |
| AC7 | Given Model S, when solving Savings to 5000 by 2027-10-01 with Groceries, then solved is false with reason "flow_does_not_affect_target", at_zero 1200.00, at_current 1200.00. | R4 | unit | test_AC7_flow_that_cannot_move_target |
| AC8 | Given Model S and a search step limit of 2, when solving Savings to 6000 by 2027-10-01 with Contribution, then solved is false with reason "did_not_converge", at_zero 0.00 and at_current 1200.00. | R4 | unit | test_AC8_unconverged_search_is_not_reported_as_solved |
| AC9 | Given Model S with inflation_rate 0.03, when solving Savings to 6000 in today's money by 2027-10-01 with Contribution, then required_amount is within 0.50 of 514.78 (6000 x 1.03^(360/365.25) / 12) and the target states values "todays_money". | R1 | unit | test_AC9_solve_for_in_todays_money |
| AC10 | Given Model L, when solving Car loan to 0 by 2027-10-01 with Car payment, then solved is true, required_amount is 860.67 (the smallest cent amount that clears 10000 at 0.5% a month in 12 payments; 860.66 leaves 0.05 owed) and reaches 0.00. | R5 | unit | test_AC10_payoff_returns_smallest_amount |
| AC11 | Given Model S plus a rate flow Sweep (Checking -> Savings, rate 0.12, rate_of Checking, monthly), when `solve_for` names Sweep, or flow "Yacht", or account "Boat", or by_date "2026-10-06", or by_date "2076-10-07", or target "lots", then each returns a tool error: the Sweep error says only fixed-amount flows can be solved; "Yacht" lists "Contribution, Groceries, Sweep"; "Boat" lists "Checking, Savings"; the date errors say after today and within 50 years; the target error names target. Given an empty model, `solve_for` errors naming `set_account`. | R6 | integration | test_AC11_solve_for_argument_checks |
| AC12 | Given Model S saved to file, when the AC1 solve and the AC5 solve run, then the file is unchanged after each and both results have `persisted: false`. | R7 | integration | test_AC12_solve_for_never_writes |

## Source behavior (only when porting or replacing existing code)
Source: the source engine's solve-for (ADR 0004).

### Kept
- One named flow is varied, measured against the real projection, from amount 0 upward.
- Tolerance max(0.1% of the target, 0.01).
- The direction is detected, not assumed.
- An unreachable target reports what the flow reaches at zero and as it stands.
- Being ahead of the goal shows as a reduction (negative change).

### Dropped or fixed, and why
- Returning the midpoint of the search as success when its steps ran out: reported as
  `did_not_converge` instead (R4), so a wrong amount is never presented as the answer.
- Measuring at the end of by_date's month: measured at the end of by_date itself (R1), so the
  answer matches the date the person gave.
- Solving on a rate flow: refused (R6); a rate has no single amount to report.
- Accepting the first amount the search lands on inside tolerance: with payments capped at the
  amount owed (Spec 0001 R11), every amount above the payoff amount leaves 0 owed, so that rule
  could return far more than needed. The smallest such amount is returned instead (R5), since
  "what payment clears the loan" means the least one. The source engine never hit this because
  it let payments run past payoff.
- Running each trial against a temporary database plan rolled back afterwards: an in-memory copy
  per Spec 0002.

## Non-goals
- Solving with more than one flow, or for a rate, a date or a growth rate.
- Bands on `solve_for`.
- Targets other than one account's balance or net worth (e.g. a reaches_zero date).
- Recommendations of any kind.

## Constraints (perf, security, compliance, compatibility)
- Same as Spec 0001: no network, stdout for MCP only, logs without financial values above DEBUG,
  numbers and stated assumptions rather than advice.
- The search step limit is a core parameter with a default large enough that every solvable
  criterion above converges; its value is an implementation choice.

## Interfaces and data shapes
| Tool | Arguments | Result |
|------|-----------|--------|
| `solve_for` | `target` (number, required); `by_date` (required); `flow` (name, required); `account` (name; omitted = net worth); `in_todays_money` (bool, default false) | see below |

Solved:
```json
{"solved": true, "flow": "Contribution", "frequency": "monthly",
 "current_amount": 100.0, "required_amount": 500.0, "change": 400.0, "reaches": 6000.0,
 "target": {"amount": 6000.0, "of": "Savings", "by_date": "2027-10-01", "values": "nominal"},
 "persisted": false}
```
Not solved:
```json
{"solved": false, "reason": "even_at_maximum", "flow": "Contribution",
 "at_zero": 0.0, "at_current": 1200.0,
 "target": {"amount": 1e12, "of": "Savings", "by_date": "2027-10-01", "values": "nominal"},
 "persisted": false}
```
Amounts and measurements are rounded to cents. With today's money, `reaches`, `at_zero` and
`at_current` are in today's money and the result also states `inflation_rate`.

## Edge cases and failure modes
- The target already met at amount 0: required_amount 0.00.
- A flow whose end_date is before today or whose start_date is after by_date: no occurrence
  counts, so `flow_does_not_affect_target`.
- A flow with no `to` (spending) against an account target it does not touch:
  `flow_does_not_affect_target`.
- A payment flow whose source account goes below zero: allowed, as in Spec 0001.
- A target of a liability above its current balance with its payment flow: `even_at_zero` (only
  borrowing would raise it).
- by_date on the last day of a month or 29 Feb: measured after that date's events.
- Corrupt or wrong-version model file: errors as in Spec 0001, file untouched.

## Open questions (must be empty before approval)
| # | Question | Proposed answer | AC that depend on it |
|---|----------|-----------------|----------------------|
| 1 | When many amounts reach the target, which amount does `solve_for` return? New with the payment cap (Spec 0001 R11): in a loan payoff every payment above the minimum leaves 0 owed. A halving search that stops at the first amount inside tolerance, as the source engine's does, returns 875.00 for Model L where 860.67 is enough. | Return the smallest amount, to the cent, whose measurement is within tolerance, when the measurement is the same at that amount and at 1,000,000,000. Otherwise any amount within tolerance, as now. | AC10 |
