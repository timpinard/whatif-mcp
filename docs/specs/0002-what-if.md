# Spec 0002: What-if
- Status: approved (AC1 to AC11 implemented at the Task 0002-T3 merge, 2026-10-09; the QA amendment
  of 2026-10-09 is implemented by Task 0002-T4)
- Owner: Timothy Pinard
- Approved by: Timothy Pinard (product owner), Timothy Pinard (engineer), Timothy Pinard (QA: AC
  sign-off, AC1 to AC11), 2026-10-08
- Amended: 2026-10-08, by the owner at the Plan 0002 quiz: R2 (the money limit covers differences),
  R3 (`applied` wording for creates and removes). 2026-10-08, by the owner at the Task 0002-T1
  review: R3 and AC6 (a one-sided account's differences count the missing side as 0).
  2026-10-09, by the owner after the QA pass (QA: Timothy Pinard; QA 0002 record): R3 (an account
  block states its kind; the flow test is on totals rounded to cents), R6 (at most 1,000 changes),
  R7 (which removed entry a create resumes); AC12 to AC15.
- Epic: Epic 0001
- Jira: (not yet created)
- Links: ADR 0001, ADR 0002, ADR 0003, ADR 0004 (all accepted). Depends on Spec 0001 (model,
  editing tools, projection). Spec 0003 builds on this spec.

## Intent (why)
The question people actually bring is "what happens if ...": save more, pay a loan off faster,
take a pay cut, make a big purchase. Answering it by editing the model and projecting again would
lose the original and leave the model changed. `what_if` applies hypothetical changes to a copy,
projects the model as it is (the baseline) and the changed copy with the same assumptions, and
returns the comparison. Nothing is saved.

## Users and scenarios
One person, on their own machine, talking to an MCP client, with a model already built (Spec 0001).

1. "What if I save $300 a month more?" -> one `set_flow` change adding a transfer.
2. "What if I pay $1,000 a month on the car loan?" -> one `set_flow` change to the payment amount;
   the answer shows the earlier payoff date and the interest saved.
3. "What if I take a 10% pay cut and also cancel the gym?" -> two changes, applied in order.
4. "What if I spend $40,000 on a kitchen next April?" -> a one-time flow; the per-period
   comparison shows when the difference appears.
5. Any of the above "in today's money".

## Requirements
| ID | Requirement (behavior, not implementation) |
|----|--------------------------------------------|
| R1 | `what_if` takes a non-empty ordered list of changes. Each change is `{"op": ...}` with op one of `set_account`, `remove_account`, `set_flow`, `remove_flow` plus that tool's arguments, validated and applied exactly as that tool would (Spec 0001 R2 to R5, R8, R16), in order, to a copy of the model. A later change sees the effects of earlier ones. |
| R2 | The baseline (the model as it is) and the hypothetical (the changed copy) are projected per Spec 0001 with the same today, `horizon_years`, `granularity` and `in_todays_money`, which take the same defaults and limits as `project` (Spec 0001 R14, R15). The limit on reported money values (Spec 0001 R14) applies to every money value in the result, differences included, with the same error as `project`. |
| R3 | The result states today, the horizon, the granularity and whether values are nominal or today's money (with the inflation rate when today's money), and contains: one description per applied change, in order: an update names the op, the name and each changed field's old and new value; a create names the op, the name, that it was created and the value of each field given; a remove names the op and the name; per period, baseline, hypothetical and difference (hypothetical minus baseline) of net worth; the end difference of net worth; per account in either model, baseline and hypothetical kind, end_balance, reaches_zero and growth_total, the end difference of balance and the difference of growth_total; per flow whose totals differ when each is rounded to cents, baseline total, hypothetical total and difference. Every difference is hypothetical minus baseline, computed from unrounded values. An account or flow present on one side only has null for the other side's block (accounts) or 0.00 for the other side's total (flows); an account's end difference of balance and difference of growth_total count the missing side as 0. |
| R4 | If any change fails, the whole call fails with an error naming the change by its 1-based position and the problem as the matching tool would report it, and returns no comparison. |
| R5 | `what_if` never writes the model file; a successful result has `persisted: false`. |
| R6 | An empty change list, a list of more than 1,000 changes, a change that is not an object, a change with no `op` or a non-text `op`, an unknown op, and a hypothetical model with no accounts are each errors; the errors about a change name it by its 1-based position, and the unknown-op error lists the four ops. A baseline model with no accounts is the same error as for `project` (Spec 0001 R14), checked before any change is applied. |
| R7 | Accounts and flows are matched between baseline and hypothetical by following each one through the changes in order: a rename (`new_name`) keeps it the same entry under its new name; a remove ends it; a create starts a new entry, except that creating a name removed earlier in the same list resumes a removed entry: the one whose baseline name is that name, if any, else the one most recently removed under that name. Each entry is listed once, under its hypothetical name, or its baseline name when it has no hypothetical side. |

## Acceptance criteria (each maps to 1+ test, in tests/test_0002_*.py)
Fixed today in every criterion: 2026-10-06. Money is compared to the cent. "File unchanged" means
the model file's bytes and modification time are identical before and after. Named model:

- Model W: Checking (asset, 5000), Savings (asset, 0), Car loan (liability, 10000, growth_rate
  0.06, an APR); flows in this order: Salary (to Checking, 4000, monthly, start 2026-11-01), Car
  payment (Checking -> Car loan, 500, monthly, start 2026-11-01). Its 1-year end net worth is
  42551.00; over 3 years Car loan reaches zero on 2028-08-01 with growth_total 562.51.

| ID | Given / When / Then | Covers | Level | Test prefix |
|----|---------------------|--------|-------|-----------|
| AC1 | Given Model W, when `what_if` gets [set_flow Extra saving (from Checking, to Savings, 300, monthly, start 2026-11-01)] with horizon_years 1, then every period's net worth difference is 0.00, end_difference is 0.00, and the end differences of balance are Savings +3600.00 and Checking -3600.00. | R1, R3 | integration | test_AC1_transfer_between_own_accounts_moves_no_net_worth |
| AC2 | Given Model W, when `what_if` gets [set_flow Salary amount 3600] with horizon_years 1, then end_difference is -4800.00 (12 occurrences x -400); `applied` has one entry naming set_flow, Salary, 4000.00 and 3600.00; the flows list Salary with baseline_total 48000.00, hypothetical_total 43200.00, difference -4800.00, and does not list Car payment. | R1, R3 | integration | test_AC2_pay_cut_and_applied_description |
| AC3 | Given Model W, when `what_if` gets [set_flow Kitchen (from Checking, 40000, one_time, start 2027-04-01)] with horizon_years 1 and granularity monthly, then the net worth difference is 0.00 for rows 2026-10 to 2027-03 and -40000.00 for rows 2027-04 to 2027-10; end_difference is -40000.00. | R2, R3 | integration | test_AC3_one_time_purchase_shows_when_difference_appears |
| AC4 | Given Model W, when `what_if` gets [set_flow Car payment amount 1000] with horizon_years 3, then Car loan reaches_zero is "2028-08-01" in the baseline and "2027-09-01" in the hypothetical; growth_total is 562.51 baseline and 284.79 hypothetical, with growth_difference -277.71; end_difference is 277.71 (the interest saved, from unrounded values: 562.506 - 284.792; not the difference of the rounded figures); Car payment totals are 10562.51 and 10284.79. | R2, R3 | integration | test_AC4_paying_loan_faster_shows_payoff_and_interest_saved |
| AC5 | Given Model W, when `what_if` gets [set_flow Gym (from Checking, 50, monthly, start 2026-11-01), set_flow Gym amount 80, remove_flow Car payment, set_account Car loan growth_rate 0.03, set_account New loan (liability, 0), set_flow Borrow (from New loan, to Checking, 1000, one_time, start 2027-01-01)] with horizon_years 1, then `applied` has 6 entries in that order; the hypothetical has one Gym with total 960.00, Car payment absent, New loan end_balance 1000.00, and Car loan end_balance 10304.16 (10000 x 1.0025^12, no payments); the baseline is Model W unchanged. | R1, R3 | integration | test_AC5_every_op_applies_in_order_and_combines |
| AC6 | Given Model W, when `what_if` gets [remove_flow Salary, set_flow Side job (to Checking, 500, monthly, start 2026-11-01), set_account New fund (asset, 1000)] with horizon_years 1, then the flows list Salary (baseline_total 48000.00, hypothetical_total 0.00) and Side job (baseline_total 0.00, hypothetical_total 6000.00) and not Car payment; the accounts list New fund with baseline null, hypothetical end_balance 1000.00, end_difference 1000.00 (1000.00 - 0) and growth_difference 0.00 (no growth rate). | R3 | integration | test_AC6_one_sided_accounts_and_flows |
| AC7 | Given Model W, when `what_if` gets [set_flow Salary amount 3600, remove_flow Yacht], then it returns a tool error containing "change 2", "Yacht" and "Salary, Car payment" and no comparison; when it gets [set_account Savings growth_rate 7], then the error contains "change 1" and "0.07". | R4 | integration | test_AC7_failing_change_named_by_position |
| AC8 | Given Model W saved to file, when the AC2 what-if succeeds and when the AC7 what-if fails, then the file is unchanged after each, and the successful result has `persisted: false`. | R5 | integration | test_AC8_what_if_never_writes |
| AC9 | Given Model W, when `what_if` gets an empty list, then it errors naming changes; when it gets a change with op "rename", then it errors containing "change 1" and listing "set_account, remove_account, set_flow, remove_flow"; when it gets [set_flow Salary amount 3600, "Salary"] or [set_flow Salary amount 3600, {"name": "Salary"}] or [set_flow Salary amount 3600, {"op": 5}], then each errors containing "change 2" and "op"; when it gets [remove_flow Salary, remove_flow Car payment, remove_account Checking, remove_account Savings, remove_account Car loan], then it errors saying the hypothetical model has no accounts. Given an empty model, when `what_if` gets [set_account Checking (asset, 1000)], then it errors naming `set_account` as `project` does, and the file is unchanged. | R6 | integration | test_AC9_invalid_change_lists_refused |
| AC10 | Given Model W and the AC2 change, when `what_if` runs with `in_todays_money`, then end_difference is -4660.29 (-4800 / 1.03^(365/365.25)) and the result states values "todays_money" and inflation_rate 0.03; with no horizon or granularity it uses 5 years and annual (6 rows); with granularity monthly and horizon_years 11 it errors as `project` does. | R2 | integration | test_AC10_projection_options_match_project |
| AC11 | Given Model W, when `what_if` gets [set_account Car loan new_name "Auto loan", set_account "auto loan" balance 8000, set_flow Car payment new_name "Loan payment" amount 600] with horizon_years 1, then the accounts list one entry "Auto loan" and none named "Car loan", with end_balance 4449.00 baseline and 1092.09 hypothetical, end_difference -3356.91, growth_total 449.00 and 292.09, growth_difference -156.91; the flows list one entry "Loan payment" and none named "Car payment", with baseline_total 6000.00, hypothetical_total 7200.00, difference 1200.00. When it gets [remove_flow Salary, set_flow Salary (to Checking, 4000, monthly, start 2026-11-01)], then the flows list is empty and end_difference is 0.00. | R3, R7 | integration | test_AC11_renamed_and_re_added_entries_match_their_baseline |
| AC12 | Given Model W, when `what_if` gets [set_flow Salary amount 4000.004] with horizon_years 1, then `applied` has one entry naming set_flow, Salary and amount (not "no change"), and the flows list Salary with difference 0.05 (12 x 0.004 = 0.048); when it gets [set_account Checking balance 5000.004], then `applied` names set_account, Checking and balance. | R1, R3 | integration | test_AC12_sub_cent_changes_are_named_in_applied |
| AC13 | Given Model W, when `what_if` gets [set_flow Salary new_name "Pay", remove_flow Pay, set_flow Salary (to Checking, 4000, monthly, start 2026-11-01)] with horizon_years 1, then the flows list is empty and end_difference is 0.00. When it gets [remove_flow Salary, set_flow Car payment new_name "Salary", remove_flow Salary, set_flow Salary (to Checking, 4000, monthly, start 2026-11-01)], then the flows list exactly one entry, Car payment, with baseline_total 6000.00, hypothetical_total 0.00 and difference -6000.00, and end_difference is -167.78 (Checking 5000 + 12 x 4000 = 53000.00; Car loan unpaid 10000 x 1.005^12 = 10616.78; 53000.00 - 10616.78 - 42551.00). | R7 | integration | test_AC13_re_created_name_resumes_its_baseline_entry_first |
| AC14 | Given Model W, when `what_if` gets 1,000 copies of [set_flow Salary amount 4000] with horizon_years 1, then it succeeds with end_difference 0.00; with 1,001 copies, it returns a tool error containing "changes" and "1,000" and no comparison, and the file is unchanged. | R6 | integration | test_AC14_change_list_limited_to_1000 |
| AC15 | Given Model W, when `what_if` gets [remove_account Savings, set_account Savings (liability, 100)] with horizon_years 1, then the accounts list one Savings entry with baseline kind "asset", end_balance 0.00, hypothetical kind "liability", end_balance 100.00, end_difference 100.00, and the result's end_difference is -100.00 (an owed 100 replaces an asset of 0). | R3, R7 | integration | test_AC15_account_blocks_state_their_kind |

## Source behavior (only when porting or replacing existing code)
Source: the source engine's what-if (ADR 0004).

### Kept
- Copy, change, project both with the same assumptions, compare.
- Nothing persists; several changes combine in one call.
- Unknown names list the candidates; an empty change list is refused.
- Per-account comparison of end balance and payoff date.

### Dropped or fixed, and why
- Writing a temporary plan to the database and rolling it back: replaced by an in-memory copy
  (ADR 0004), so a crash cannot leave a half-applied change.
- Flow differences estimated as per-occurrence change x frequency x horizon, ignoring start and
  end dates: replaced by exact flow totals from both projections.
- Saving a what-if as a plan, and the record of the last what-if kept for that: dropped, there are
  no saved scenarios.
- Thinning the comparison to a handful of checkpoints: the caller picks granularity.

## Non-goals
- Saving, naming or listing what-ifs; comparing more than one hypothetical in a call.
- Bands on `what_if` (Spec 0004 covers `project` only).
- Changing the inflation rate inside a what-if (`set_inflation_rate` is not an op).
- Recommendations of any kind.

## Constraints (perf, security, compliance, compatibility)
- Same as Spec 0001: no network, stdout for MCP only, logs without financial values above DEBUG,
  numbers and stated assumptions rather than advice.
- The model file is read once per call and never written (R5).

## Interfaces and data shapes
| Tool | Arguments | Result |
|------|-----------|--------|
| `what_if` | `changes` (list, required); `horizon_years` (int, default 5); `granularity` (default `annual`); `in_todays_money` (bool, default false) | see below |

A change is `{"op": "<tool name>", ...that tool's arguments}`, for example
`{"op": "set_flow", "name": "Salary", "amount": 3600}`.

```json
{
  "today": "2026-10-06",
  "horizon": {"years": 1, "from": "2026", "to": "2027", "end_date": "2027-10-06"},
  "granularity": "annual",
  "values": "nominal",
  "applied": ["set_flow 'Salary': amount 4000.00 -> 3600.00"],
  "net_worth": [{"period": "2026", "end_date": "2026-12-31",
                 "baseline": 0.0, "hypothetical": 0.0, "difference": 0.0}],
  "end_difference": -4800.0,
  "accounts": [{"name": "Checking",
                "baseline": {"kind": "asset", "end_balance": 0.0, "reaches_zero": null, "growth_total": 0.0},
                "hypothetical": {"kind": "asset", "end_balance": 0.0, "reaches_zero": null, "growth_total": 0.0},
                "end_difference": 0.0, "growth_difference": 0.0}],
  "flows": [{"name": "Salary", "baseline_total": 48000.0, "hypothetical_total": 43200.0,
             "difference": -4800.0}],
  "persisted": false
}
```
`inflation_rate` is present only when `values` is `todays_money`. Accounts and flows are matched
and named as R7 states. The
`applied` wording is illustrative; each entry must name the op, the name and the old and new
value of each changed field. Account and net worth values shown as 0.0 are placeholders.

## Edge cases and failure modes
- A change that adds then a later change that updates the same flow: the later one wins.
- A change that renames an account or flow: later changes use the new name; flows stay attached;
  the comparison shows one entry under the new name (R7).
- A remove followed by a create of the same name: one entry, compared with its baseline (R7).
- A rename, a remove under the new name, then a create of the baseline name: one entry, compared
  with its baseline (R7).
- A rename onto a name removed earlier in the list: the renamed entry keeps its own baseline, and
  the removed one is listed under its baseline name with hypothetical null, so two entries share
  that name (R7).
- A change that removes an account still used by a flow: fails as `remove_account` would, named
  by position.
- A change list that removes every account: error, no comparison.
- A change identical to the model (e.g. Salary amount 4000): allowed; every difference is 0.00
  and the flows list is empty.
- A one_time change dated on or before today: fails as `set_flow` would (it would never fire).
- Corrupt or wrong-version model file: errors as in Spec 0001, file untouched.

## Open questions (must be empty before approval)
| # | Question | Proposed answer | AC that depend on it |
|---|----------|-----------------|----------------------|
