# Spec 0004: Monte Carlo bands
- Status: draft
- Owner: Timothy Pinard
- Links: ADR 0001, ADR 0002, ADR 0003, ADR 0004 (all accepted). Depends on Spec 0001 (model,
  growth rules, `project`). Independent of Spec 0002 and Spec 0003.

## Intent (why)
A projection with a fixed 7% return reads as a promise. Investments do not grow at their average
rate every year, and the person should see how wide the outcome could be. The `bands` option of
`project` runs many simulations in which each account with a volatility gets a different growth
rate each year, and reports the 10th, 50th and 90th percentiles per period alongside the
deterministic projection.

## Users and scenarios
One person, on their own machine, talking to an MCP client, with a model already built (Spec 0001)
and a volatility set on accounts whose returns vary (`set_account ... volatility=0.15`).

1. "How wide could my brokerage outcome be in ten years?" -> `project` with `bands`.
2. "Show me that again, same numbers" -> the same `seed`.
3. "And in today's money?" -> `bands` with `in_todays_money`.

## Requirements
| ID | Requirement (behavior, not implementation) |
|----|--------------------------------------------|
| R1 | `project` accepts `bands` (bool, default false), `simulations` (whole number 100 to 2000, default 500) and `seed` (integer, optional). `simulations` or `seed` given without `bands: true` is an error naming `bands`. Other arguments and their limits are as in Spec 0001 R14. |
| R2 | Each simulation is the Spec 0001 projection with one difference: each account with volatility above zero uses, for every growth step in a calendar year, a rate drawn once for that account and year from Normal(growth_rate, volatility), clipped below at -1.0. The draw is used as that account's growth_rate under Spec 0001 R12 (effective annual for an asset, APR for a liability, no growth at or below zero). Draws are independent across accounts, years and simulations; a year's draw for an account is taken before that year's first growth step, and only for years that have a growth step. Accounts with volatility 0 and all flows behave exactly as in Spec 0001. |
| R3 | The result keeps every field of the projection without bands unchanged and adds `simulations` (the count run) and `bands`: for net worth and for each account, one entry per period (same labels as the rows) with p10, p50 and p90 of that period's values across simulations. Net worth percentiles are taken over each simulation's net worth, not summed from account percentiles. A percentile p of n values is the value at rank ceil(p / 100 x n) in ascending order (nearest rank, 1-based). |
| R4 | When no account has volatility above zero, `bands` and `simulations` are null and `bands_note` says no account has volatility above zero; the rest of the result is as without bands. |
| R5 | The same seed, model and arguments give identical bands. |
| R6 | With `in_todays_money`, band values are deflated exactly as the row they belong to (Spec 0001 R15). |
| R7 | `project` with bands never writes the model file. |
| R8 | `project` with bands returns within the bands latency budget. (Open question 1.) |

## Acceptance criteria (each maps to 1+ test, in tests/test_0004_*.py)
Fixed today in every criterion: 2026-10-06. Money is compared to the cent. "File unchanged" means
the model file's bytes and modification time are identical before and after. Named model:

- Model V: Brokerage (asset, 100000, growth_rate 0.07, volatility 0.15), Checking (asset, 1000);
  no flows.

"A source that returns x" means the simulation is given a random source whose every normal draw
is x, in place of the seeded one.

| ID | Given / When / Then | Covers | Level | Test name |
|----|---------------------|--------|-------|-----------|
| AC1 | Given Model V, when `project` runs with horizon_years 10, granularity annual, `bands: true`, seed 7, then `bands` has net_worth and Brokerage and Checking entries for the 11 periods "2026" to "2036"; in every entry p10 <= p50 <= p90; the last period's Brokerage p90 - p10 is greater than the first period's; `periods`, `accounts` and `flows` equal those of the same call without bands; `simulations` is 500. | R1, R2, R3 | integration | test_AC1_bands_ordered_widening_and_beside_deterministic_rows |
| AC2 | Given Model V, when the AC1 call runs twice, then both `bands` are identical; Checking's p10, p50 and p90 each equal 1000.00 in every period; net worth p10, p50 and p90 each equal Brokerage's plus 1000.00. | R3, R5 | integration | test_AC2_same_seed_same_bands_and_fixed_accounts_flat |
| AC3 | Given Checking (asset, 1000) and Savings (asset, 500, growth_rate 0.04) with volatility 0, when `project` runs with `bands: true`, then `bands` is null, `simulations` is null, `bands_note` says no account has volatility above zero, and `periods`, `accounts` and `flows` equal those of the call without bands. | R4 | integration | test_AC3_no_volatility_means_no_bands |
| AC4 | Given Model V, when `project` runs with `bands: true` and simulations 50 or 5000 or 250.5, then each errors naming simulations and "100 to 2000"; with seed "abc", it errors naming seed; with `simulations=200` or `seed=7` but no `bands`, it errors naming bands. In each error case the file is unchanged. | R1 | integration | test_AC4_bands_argument_checks |
| AC5 | Given Brokerage (asset, 1000, growth_rate 0.07, volatility 0.15) and Checking (asset, 1000, volatility 0), and a source that records each draw request and returns 0.10 for the first and 0.20 for every later one, when 100 simulations of a 2-year monthly projection run, then each simulation requests exactly 3 draws (years 2026, 2027, 2028), all for Brokerage with mean 0.07 and standard deviation 0.15; Brokerage is 1016.01 at end of 2026-12 (1000 x 1.10^(2/12)) and 1219.21 at end of 2027-12 (x 1.20) in every simulation, so p10 = p50 = p90 there. | R2 | unit | test_AC5_one_draw_per_account_per_calendar_year |
| AC6 | Given Brokerage (asset, 1000, growth_rate 0.07, volatility 0.15) and a source that returns 0.07, when 100 simulations of a 1-year monthly projection run, then Brokerage's p10, p50 and p90 equal the deterministic rows in every period (1070.00 in the last); with `in_todays_money` they equal the deterministic today's-money rows (1038.86 in the last: 1070 / 1.03^(365/365.25)). | R2, R6 | unit | test_AC6_draws_follow_spec_0001_growth_rules |
| AC7 | Given Brokerage (asset, 1000, growth_rate 0.07, volatility 0.5), Card (liability, 1200, growth_rate 0.12, volatility 0.5) and a source that returns -1.5, when 100 simulations of a 1-year monthly projection run, then Brokerage is 1000.00 at end of 2026-10 and 0.00 from end of 2026-11 on (draw clipped to -1.0: (1 - 1)^(1/12) - 1 = -100% in the first month); Card is 1100.00 at end of 2026-11 and 1008.33 at end of 2026-12 (clipped APR -1.0: -1/12 a month). | R2 | unit | test_AC7_draws_clipped_at_minus_one |
| AC8 | Given a period whose simulated values are 1, 2, ..., 100 in shuffled order, then its band is p10 10, p50 50, p90 90; given 1, 2, ..., 500, then p10 50, p50 250, p90 450. | R3 | unit | test_AC8_nearest_rank_percentiles |
| AC9 | Given Model V saved to file, when the AC1 call runs, then the file is unchanged. | R7 | integration | test_AC9_bands_never_write |
| AC10 | Given 25 accounts with growth_rate 0.05 and volatility 0.15 and 25 monthly fixed flows between them, when `project` runs with horizon_years 30, granularity annual, `bands: true` and default simulations, then it returns within the bands latency budget. | R8 | integration | test_AC10_bands_within_latency_budget |

## Source behavior (only when porting or replacing existing code)
Source: the source engine's Monte Carlo projection (ADR 0004).

### Kept
- A rate drawn once per (account, calendar year) from Normal(rate, volatility), the rest of the
  projection deterministic.
- p10, p50, p90 per period; seedable for repeatable runs; default 500 simulations.

### Dropped or fixed, and why
- Default volatility heuristic (0.15 for investment growth, 0.05 for debt): volatility is 0
  unless the person sets it, so no band appears that they did not ask for.
- Volatility on rate flows: volatility belongs to the account's growth rate (Spec 0001 R12), the
  only rate that varies by market.
- Unclipped draws: clipped at -1.0, because a draw below -100% flips the sign of a balance and,
  for an asset, has no monthly equivalent.
- Percentile as the value at index round(p / 100 x (n - 1)): replaced by the standard nearest-rank
  definition (R3), so the meaning does not depend on a language's rounding of halves.
- Bands for accounts only: net worth bands added, taken over each simulation's net worth (R3).

## Non-goals
- Bands on `what_if` or `solve_for`.
- Correlation between accounts, or between years.
- Distributions other than normal; fat tails.
- Percentiles other than 10, 50, 90.
- Volatility on flows or on the inflation rate.
- numpy or any new dependency (ADR 0002); see Open question 1.

## Constraints (perf, security, compliance, compatibility)
- ADR 0002: pure Python, no numpy; missing the latency budget is the trigger to revisit that.
- Latency: see Open question 1. `project` without bands keeps its own budget (Spec 0001 R18).
- Bands describe spread under the stated assumptions; they are not a probability forecast or
  advice, and the result says how many simulations produced them.

## Interfaces and data shapes
`project` arguments added: `bands` (bool, default false); `simulations` (int, default 500); `seed`
(int, optional). Keys added to the result only when `bands` is true:

```json
{
  "simulations": 500,
  "bands": {
    "net_worth": [{"period": "2026", "p10": 0.0, "p50": 0.0, "p90": 0.0}],
    "accounts": {"Brokerage": [{"period": "2026", "p10": 0.0, "p50": 0.0, "p90": 0.0}]}
  },
  "bands_note": null
}
```
With no volatile account: `"simulations": null, "bands": null, "bands_note": "No account has
volatility above zero."`. Values are rounded to cents; the 0.0 values are placeholders.

## Edge cases and failure modes
- Volatile account at or below zero: no growth that step, whatever the draw (Spec 0001 R12).
- A draw at or below -1.0 for an asset: the balance becomes 0.00 at that year's first growth step
  and then earns nothing until flows lift it above zero.
- Volatility with growth_rate 0: draws centred on 0.
- Volatile liability: interest varies by year; a negative draw lowers the amount owed.
- A rate flow whose rate_of is a volatile account: its amounts vary by simulation, so the
  receiving account gets a band too.
- A calendar year with no growth step inside the horizon (today on or after the horizon's last
  1st): no draw for it.
- Seed omitted: each call gives different bands.

## Open questions (must be empty before approval)
| # | Question | Proposed answer | AC that depend on it |
|---|----------|-----------------|----------------------|
| 1 | What is the latency budget for `project` with bands? | Measure in the first implementation task; if 500 simulations over 30 years with monthly growth steps (annual granularity, since Spec 0001 limits monthly rows to 10 years) exceed 3 s on the model of about 50 volatile accounts and flows, reduce the default simulations or raise an ADR for numpy. | AC10 |
