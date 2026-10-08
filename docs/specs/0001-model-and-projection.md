# Spec 0001: Model and projection
- Status: implemented (Task 0001-T7 merged 2026-10-07; full gate green); amended after the QA
  pass, fix tasks Task 0001-T8 to T10 open
- Approved by: Timothy Pinard, 2026-10-06
- Amended: 2026-10-06, before implementation, by the owner: answers to the plan's spec gaps
  (R1, R2, R4, R14, R19, rounding under Interfaces). 2026-10-07, before Task 0001-T2, by the
  owner (QA: Timothy Pinard): answers to the re-plan's spec gaps (R2, R4, AC26); then, at the
  Task 0001-T3 merge gate, R1 (file accounts and flows held to R2 and R4 rules); and at the Task
  0001-T5 merge gate, R1 (file inflation rate held to the range `set_inflation_rate` allows); and
  at the Task 0001-T6 merge gate, R4 (a flow has at least one side, and its sides differ).
  2026-10-07, after the QA pass, by the owner (QA: Timothy Pinard): QA findings F1 to F10 (R1,
  R2, R4, R13, R14, R16, Interfaces rounding, Edge cases, AC27 to AC34). 2026-10-08, at the Task
  0001-T8 review, by the owner: AC27's arithmetic corrected (7.2 x 10^26, not 7 x 10^20); at the
  Task 0001-T10 review, R4's start_date limit made a fixed floor (1900-01-01) so a valid file
  never becomes invalid with time; AC33 and AC34 restated.
- Owner: Timothy Pinard
- Links: ADR 0001, ADR 0002, ADR 0003, ADR 0004 (all accepted). Foundation for Spec 0002 (what-if),
  Spec 0003 (solve-for, via Spec 0002) and Spec 0004 (bands). Implement this spec first.

## Intent (why)
A person wants to ask an AI assistant "where will my money be?" and get numbers that come from
arithmetic, not from the assistant's own estimates. They describe their accounts and recurring
flows once; the server keeps that model in a local file they own and projects balances forward
with math ported from the source engine (ADR 0004). This spec covers building and inspecting the
model and the deterministic projection that the what-if, solve-for and bands specs build on. The
output states numbers and assumptions, never advice.

## Users and scenarios
One person, on their own machine, talking to an AI assistant through an MCP client.

1. Build the model: "I have $5,000 in checking, a car loan of $10,000 at 6% that I pay $500 a
   month, and I'm paid $4,000 a month." The assistant calls `set_account` and `set_flow` until
   `show_model` matches what the person said.
2. Correct the model: "Actually the car payment is $700, and it ends next December." ->
   `set_flow` with only the changed fields.
3. Look ahead: "Where will I be in five years?" -> `project`.
4. Real terms: "...in today's money" -> `project` with `in_todays_money`.

## Requirements
| ID | Requirement (behavior, not implementation) |
|----|--------------------------------------------|
| R1 | The model lives in one JSON file: path from env var `WHATIF_MODEL_PATH`, else `~/.whatif/model.json` (ADR 0003). A leading `~` in `WHATIF_MODEL_PATH` is expanded to HOME, an empty value counts as unset, and a relative path makes every tool fail with an error naming `WHATIF_MODEL_PATH`. A missing file is an empty model (no accounts, no flows, inflation rate 0.03) and is not created by reads. The first write creates missing parent directories with mode 0700 and the file with mode 0600. Every write replaces the file atomically; a failed write leaves the previous file intact. When the model path is a symlink, a write replaces the link's target and keeps the link. The file carries `"version": 1`. A file that is not valid JSON (including bytes that are not UTF-8 and nesting too deep to parse), that exists but cannot be read, or that has another version makes every tool fail with an error naming the path and the problem, and the file is never overwritten in that state. A file that is valid JSON with version 1 but does not match the version 1 shape is treated the same as invalid JSON; an account or flow in the file that breaks a rule R2 or R4 states for it, or an inflation rate outside the range `set_inflation_rate` allows (greater than -1 and less than 1), does not match the shape; nor does a key the version 1 shape does not define, or a key repeated within one object. |
| R2 | `set_account` creates an account (name, kind `asset` or `liability`, balance, optional growth_rate default 0, optional volatility default 0) or, when the name already exists, updates only the fields given. It renames via `new_name`; flows that use the account stay attached. Liability balances are amounts owed, never negative. Each account records `balance_as_of`: the date its balance was last set. Volatility is stored and validated here and used only by bands (Spec 0004). Giving a balance always sets balance_as_of to today, even when the value is unchanged. A balance is at most 1,000,000,000,000 in absolute value. Giving `kind` to an existing account changes it; the resulting account is validated as a new one would be (a liability balance is never negative). |
| R3 | `remove_account` deletes an account, but refuses while any flow uses it as `from`, `to` or `rate_of`, listing those flows. |
| R4 | `set_flow` creates a flow (name; optional `from` and `to` accounts, an omitted side being outside, at least one of them given and the two different; either a fixed `amount` or a `rate` of the `rate_of` account's balance; frequency; start_date default today; optional end_date) or, when the name already exists, updates only the fields given. Giving `amount` to a rate flow makes it fixed and clears rate and rate_of; giving `rate` and `rate_of` to a fixed flow clears amount. A field passed as JSON null clears it (`end_date`, `from`, `to`). It renames via `new_name`. Every result lists `similar_flows`: other flows with the same from, to and frequency. Accounts named in a flow must exist; they are never created by `set_flow`. A fixed `amount` must be greater than 0 and at most 1,000,000,000,000; a `rate` must be above 0 and at most 1. A `start_date` is on or after 1900-01-01. On update, the resulting flow must satisfy every rule for a new flow, except that the one_time never-fires check applies only when `start_date` or `frequency` is given. `rate_of` without `rate` is an error naming `rate`, unless the flow is already a rate flow, where it changes the rate_of account. |
| R5 | `remove_flow` deletes a flow. |
| R6 | `set_inflation_rate` sets the model's annual inflation rate used for today's money and returns it with the previous value. |
| R7 | `show_model` returns today, every account, every flow, the inflation rate, net worth today (from the stored balances) and the model file path. |
| R8 | Account and flow names are matched case-insensitively after trimming surrounding whitespace, exactly, never by substring or similarity. A name that matches nothing, where an existing one is required, is an error listing the existing names of that kind; `set_account` on an unknown name without `kind` says the account does not exist and lists the existing account names. Names are unique per kind regardless of case; the stored spelling is kept until `new_name` changes it. |
| R9 | Each flow has occurrences: dates it fires, generated from start_date by frequency up to and including end_date. `weekly` and `biweekly` step 7 and 14 days. `monthly`, `quarterly`, `semiannual` and `annual` step 1, 3, 6 and 12 calendar months, always anchored to the start day and clamped to the last day of shorter months (never drifting). `semimonthly` fires twice in every month: on the start day and on a second day (start day + 15 when the start day is 15 or less, else start day - 15), each clamped to the month's last day. `one_time` fires once, on start_date. Only occurrences strictly after today and on or before the horizon end take effect: balances entered today already include today. |
| R10 | The amount of an occurrence is the fixed amount, or `rate x balance of rate_of / occurrences per year` (weekly 52, biweekly 26, semimonthly 24, monthly 12, quarterly 4, semiannual 2, annual 1, one_time 1) using the rate_of balance at that moment; a rate_of balance at or below zero gives zero. |
| R11 | An occurrence moves its amount from `from` to `to`. Leaving an asset lowers it; arriving in an asset raises it. Leaving a liability raises the amount owed (borrowing); arriving in a liability lowers it (payment). A movement into a liability is capped at the amount currently owed, and the `from` side moves by the same capped amount. Assets may go below zero. |
| R12 | Growth is applied on the 1st of every month strictly after today and on or before the horizon end, to each account whose balance is above zero; an account at or below zero gets no growth that day. An asset's growth_rate is an effective annual rate: each month it grows by `balance x ((1 + growth_rate) ^ (1/12) - 1)`, so a balance with no flows grows by exactly growth_rate over 12 months. A liability's growth_rate is an APR: each month the amount owed rises by `balance x growth_rate / 12`. On any date, growth of all accounts is applied first, then flows in the order they were first added to the model. |
| R13 | `project` returns: today; the horizon stated explicitly (years, first and last period label, end_date = today's date the given number of years ahead, 28 Feb when that date does not exist); the granularity; one row per period from the period containing today to the period containing the horizon end, each with its label, end_date, every account's balance and net worth; a per-account summary (kind, start_balance, end_balance, reaches_zero, growth_total); and a per-flow total moved over the horizon. A row's values are taken after all events of the earlier of the period's last day and the horizon end, so the last row does not depend on granularity. Net worth is the sum of asset balances minus the sum of liability balances. reaches_zero compares the balance rounded to cents, and no money value is reported as -0.00. |
| R14 | `project` takes `horizon_years`, a whole number 1 to 50 (default 5; an integral value such as 5.0 is accepted, 5.5 is refused), and `granularity`, one of `monthly`, `quarterly`, `annual` (default `annual`). `monthly` is allowed only for horizons of 10 years or less; a longer monthly request is an error that suggests `quarterly` or `annual`. A model with no accounts is an error naming `set_account`. A projection in which any reported money value reaches 1,000,000,000,000,000 in absolute value, or is not finite, is an error naming `horizon_years` and the growth or inflation rate as the values to reduce. |
| R15 | With `in_todays_money`, every money value in the projection result is divided by `(1 + inflation_rate) ^ (days from today to its date / 365.25)`, where a row's date is its end_date, start balances are today's and the other summary values and flow totals use the horizon end; the result states the inflation rate used. |
| R16 | Every invalid input is an MCP tool error (`isError: true`) whose message names the argument or name at fault and how to fix it, and leaves the model file unchanged; a tool that returns an error has not changed the file. Rates are decimals; out-of-range rates are refused with a hint such as "0.07 means 7%". |
| R17 | `show_model` and `project` never write the model file. |
| R18 | `project` returns in under 1 second for a 30-year horizon on a model of about 50 accounts and flows. |
| R19 | Nothing but MCP messages is written to stdout. Logs go to stderr and carry no account names, flow names or amounts above DEBUG. Logging is at INFO; v1 has no setting to change the level. |

## Acceptance criteria (each maps to 1+ test, in tests/test_0001_*.py)
Fixed today in every criterion: 2026-10-06. Money is compared to the cent. "File unchanged" means
the model file's bytes are identical before and after (or it still does not exist). Named model:

- Model W: Checking (asset, 5000), Savings (asset, 0), Car loan (liability, 10000, growth_rate
  0.06); flows in this order: Salary (to Checking, 4000, monthly, start 2026-11-01), Car payment
  (Checking -> Car loan, 500, monthly, start 2026-11-01).

| ID | Given / When / Then | Covers | Level | Test name |
|----|---------------------|--------|-------|-----------|
| AC1 | Given `WHATIF_MODEL_PATH` unset and HOME set to an empty temp dir, when `show_model` is called, then model_path is `<HOME>/.whatif/model.json`. Given `WHATIF_MODEL_PATH` set to `<tmp>/new/model.json` (no `new` dir), when `show_model` is called, then it returns no accounts, no flows, inflation_rate 0.03, net_worth_today 0.00, model_path that path, and no file or dir is created; when `set_account(name="Checking", kind="asset", balance=5000)` succeeds, then the dir and file exist, the file mode is 0600, its JSON has `"version": 1`, and nothing exists under `<HOME>/.whatif`; when `show_model` and `project` are then called, the file's bytes and modification time are unchanged. | R1, R7, R17 | integration | test_AC1_model_file_location_creation_and_read_only_tools |
| AC2 | Given the model file contains `{not json`, when `show_model` or `set_account(name="X", kind="asset", balance=1)` is called, then each returns a tool error containing the file path and "not valid JSON". Given the file has `"version": 2`, when `project` is called, then it returns a tool error containing "version 2" and the path. In every case the file is unchanged. | R1, R16 | integration | test_AC2_unreadable_file_errors_and_is_not_overwritten |
| AC3 | Given a model file holding Model W, when a write of a changed model fails at the final replace step, then the write raises an error and the file's bytes equal the original. | R1 | unit | test_AC3_failed_write_leaves_previous_file_intact |
| AC4 | Given an empty model, when `set_account(name="Checking", kind="asset", balance=5000)` is called, then the result has `created: true` and `show_model` lists Checking with balance 5000.00, growth_rate 0, volatility 0, balance_as_of "2026-10-06". Given a model file where Checking (asset, 5000) has balance_as_of "2026-09-01", when `set_account(name=" checking", growth_rate=0.01)` is called, then `created: false`, `previous` shows growth_rate 0, and the name ("Checking"), balance and balance_as_of are unchanged; when `set_account(name="Checking", balance=6000)` is then called, balance_as_of becomes "2026-10-06". | R2, R8 | integration | test_AC4_set_account_creates_with_defaults_and_updates_given_fields |
| AC5 | Given Model W, when `set_account(name="Car loan", new_name="Auto loan")` is called, then `show_model` shows Car payment going to "Auto loan"; when `set_account(name="Savings", new_name="checking")` is called, then it errors naming the existing "Checking" and the file is unchanged; when `set_account(name="checking", new_name="CHECKING")` is called, then the stored name becomes "CHECKING". | R2, R8 | integration | test_AC5_rename_account_keeps_flows_and_rejects_collision |
| AC6 | Given Model W, when `set_account` is called with each of: `name="Chekcing", balance=6000` (unknown, no kind); `name="X", kind="asset"` (no balance); `name="X", kind="loan", balance=1`; `name="  ", kind="asset", balance=1`; `name="X", kind="liability", balance=-1`; `name="X", kind="asset", balance="lots"`; and `name="X", kind="asset", balance=1` with growth_rate 7, growth_rate -1, growth_rate 1.5, volatility -0.1 or volatility 1.5, then each returns a tool error naming the argument at fault; the first lists "Checking, Savings, Car loan" and says `kind` and `balance` create a new account; the kind error lists "asset, liability"; the growth_rate 7 error contains "decimal" and "0.07"; the file is unchanged after each. Allowed: growth_rate greater than -1 and at most 1; volatility 0 to 1. | R2, R8, R16 | integration | test_AC6_set_account_validation |
| AC7 | Given Model W plus Old (asset, 0), Brokerage (asset, 1000) and Dividend (to Checking, rate 0.02, rate_of Brokerage, quarterly), when `remove_account(name="old")` is called, then Old is gone; when `remove_account(name="Car loan")` or `remove_account(name="Brokerage")` is called, then each errors naming "Car payment" or "Dividend" respectively, and both accounts remain. | R3, R8 | integration | test_AC7_remove_account_refused_while_referenced |
| AC8 | Given Model W: when `set_flow(name="Gym", from="Checking", amount=50, frequency="monthly")` is called, then `created: true` and Gym has to null, start_date "2026-10-06", end_date null, rate null; when `set_flow(name="Extra car payment", from="Checking", to="Car loan", amount=100, frequency="monthly", start_date="2026-11-01")` is called, then `similar_flows` is ["Car payment"]; when `set_flow(name="Car payment", end_date="2027-12-01")` and then `set_flow(name="car payment", amount=700, end_date=null)` are called, then the second has `created: false`, `previous` amount 500.00, and Car payment has amount 700.00, end_date null and its from, to, frequency and start_date unchanged; when `set_flow(name="Sweep", from="Checking", to="Savings", rate=0.12, rate_of="Checking", frequency="monthly")` and then `set_flow(name="Sweep", amount=50)` are called, then Sweep has amount 50.00 and rate and rate_of null; when `set_flow(name="Gym", new_name="Fitness")` is called, then Fitness replaces Gym; when `set_flow(name="Fitness", new_name="salary")` is called, then it errors naming "Salary". | R4, R8 | integration | test_AC8_set_flow_creates_updates_and_renames |
| AC9 | Given Model W, when `set_flow` is called with each of: no from and no to; from equal to to; both amount and rate; neither amount nor rate; rate without rate_of; amount 0; amount "lots"; rate 0; rate 1.5; end_date before start_date; frequency "daily"; start_date "10/1/2026"; frequency one_time with start_date "2026-10-06"; to "Marina"; rate_of "Marina", then each returns a tool error naming the argument at fault; the one_time error says it would never fire; the "Marina" errors contain "Marina" and "Checking, Savings, Car loan"; no account is created and the file is unchanged after each. | R4, R9, R16 | integration | test_AC9_set_flow_validation |
| AC10 | Given Model W, when `remove_flow(name="Sal")` is called, then it errors (no substring match) listing "Salary, Car payment" and nothing is removed; when `remove_flow(name="  car PAYMENT ")` is called, then Car payment is removed and Salary remains; when `remove_flow(name="Car payment")` is called again, then it errors listing "Salary". | R5, R8 | integration | test_AC10_remove_flow_and_exact_case_insensitive_names |
| AC11 | Given Model W, when `show_model` is called, then it returns today "2026-10-06"; 3 accounts each with name, kind, balance, growth_rate, volatility, balance_as_of; 2 flows in order Salary, Car payment, each with name, from, to, amount, rate, rate_of, frequency, start_date, end_date; inflation_rate 0.03; net_worth_today -5000.00; and the model path. | R7 | integration | test_AC11_show_model_contents |
| AC12 | Given each start date and frequency, then the occurrences begin: monthly from 2027-01-31: 2027-01-31, 2027-02-28, 2027-03-31, 2027-04-30, and include 2028-02-29; quarterly from 2026-11-30: 2026-11-30, 2027-02-28, 2027-05-30; semiannual from 2026-11-30: 2026-11-30, 2027-05-30, 2027-11-30; annual from 2028-02-29: 2028-02-29, 2029-02-28, 2030-02-28, 2031-02-28, 2032-02-29; weekly from 2026-10-07: 2026-10-07, 2026-10-14, 2026-10-21; biweekly from 2026-10-07: 2026-10-07, 2026-10-21, 2026-11-04. | R9 | unit | test_AC12_calendar_stepping_stays_anchored |
| AC13 | Given semimonthly from 2026-10-20, then occurrences begin 2026-10-20, 2026-11-05, 2026-11-20, 2026-12-05; from 2027-01-30, they begin 2027-01-30, 2027-02-15, 2027-02-28, 2027-03-15, 2027-03-30; from 2026-10-01, exactly 24 fall in 2026-10-01 to 2027-09-30. | R9 | unit | test_AC13_semimonthly_twice_every_month |
| AC14 | Given Checking (asset, 1000) and flows Rent (from Checking, 100, monthly, start 2026-01-15, end 2026-12-15), Tip (to Checking, 10, monthly, start 2026-10-06), Kitchen (from Checking, 1000, one_time, start 2027-04-01) and Bonus (to Checking, 100, annual, start 2027-10-07), when projecting 1 year monthly, then Checking is 900.00 at end of 2026-10, 810.00 at end of 2026-11, 720.00 at end of 2026-12, 750.00 at end of 2027-03, -240.00 at end of 2027-04 and -180.00 at the last row (2027-10-06) (Rent fires on 2026-10-15, 11-15, 12-15 only; Tip fires 12 times, not today but on the horizon end; Kitchen once; Bonus after the horizon end never); flow totals are Rent 300.00, Tip 120.00, Kitchen 1000.00, Bonus 0.00. | R9, R11, R13 | unit | test_AC14_occurrences_that_take_effect |
| AC15 | Given Brokerage (asset, 100000), Checking (asset, 0) and Drawdown (Brokerage -> Checking, rate 0.04, rate_of Brokerage, annual, start 2027-01-01), when projecting 1 year, then Checking ends at 4000.00; with Drawdown monthly, rate 0.12, start 2026-11-01, its first two occurrences move 1000.00 and 990.00; with Brokerage at -50, Drawdown moves 0.00 every time. | R10 | unit | test_AC15_rate_flow_uses_balance_at_occurrence |
| AC16 | Given Checking (asset, 1000), Loan (liability, 0), Borrow (Loan -> Checking, 300, one_time, start 2026-11-01) and Pay (Checking -> Loan, 500, monthly, start 2026-12-01), when projecting 1 year monthly, then at end of 2026-11 Loan is 300.00, Checking 1300.00 and net worth 1000.00; at end of 2026-12 and every later row Loan is 0.00 and Checking 1000.00; the Pay total is 300.00; Loan reaches_zero is "2026-12-01". | R11, R13 | unit | test_AC16_borrowing_and_payment_capped_at_amount_owed |
| AC17 | Given Savings (asset, 1000, growth_rate 0.07), Overdrawn (asset, -500, growth_rate 0.12) and Empty (asset, 0, growth_rate 0.12), when projecting 1 year monthly, then Savings is 1000.00 at end of 2026-10, 1005.65 at end of 2026-11 (1000 x 1.07^(1/12)), 1011.34 at end of 2026-12 and 1070.00 at the last row (12 steps: 1000 x 1.07), with growth_total 70.00; projecting 2 years annual, Savings' last row is 1144.90 (1000 x 1.07^2); Overdrawn stays -500.00 and Empty 0.00 in every row, both with growth_total 0.00. | R12 | unit | test_AC17_asset_growth_is_effective_annual_and_none_at_or_below_zero |
| AC18 | Given Model W, when projecting 1 year monthly, then Car loan is 10000.00 at end of 2026-10, 9550.00 at end of 2026-11 (10000 + 50 - 500) and 9097.75 at end of 2026-12 (9550 + 47.75 - 500; interest before the same-day payment), 4449.00 at the last row, with growth_total 449.00. Given Card (liability, 1200, growth_rate 0.12) and Paid off (liability, 0, growth_rate 0.2) with no flows, when projecting 1 year, then Card ends at 1352.19 (1200 x 1.01^12, not 1344.00) and Paid off at 0.00 with growth_total 0.00. | R12, R13 | unit | test_AC18_liability_interest_is_apr_monthly_before_flows |
| AC19 | Given Checking (asset, 1000), Savings (asset, 0), Spend (from Checking, 500, monthly, start 2026-11-01) added first and Sweep (Checking -> Savings, rate 0.12, rate_of Checking, monthly, start 2026-11-01) added second, when projecting, then Sweep moves 5.00 on 2026-11-01; with Sweep added first instead, it moves 10.00. | R12 | unit | test_AC19_same_day_flows_apply_in_model_order |
| AC20 | Given Model W, when projecting 1 year, then monthly gives 13 rows "2026-10" to "2027-10" with the first end_date 2026-10-31; quarterly 5 rows "2026-Q4" to "2027-Q4" with the first end_date 2026-12-31; annual 2 rows "2026", "2027" with the first end_date 2026-12-31; in all three the last row's end_date is 2027-10-06, its balances are Checking 47000.00, Savings 0.00, Car loan 4449.00 and its net worth 42551.00; in every row net_worth equals the asset balances minus the liability balance. | R13 | unit | test_AC20_period_rows_and_granularity_independent_end |
| AC21 | Given Model W, when projecting 3 years annual, then the result states today "2026-10-06" and horizon {years 3, from "2026", to "2029", end_date "2029-10-06"}; the account summary is Checking 5000.00 -> 138437.49, reaches_zero null; Savings 0.00 -> 0.00, reaches_zero null; Car loan 10000.00 -> 0.00, reaches_zero "2028-08-01", growth_total 562.51; flow totals are Salary 144000.00 and Car payment 10562.51. | R13 | unit | test_AC21_account_summary_flow_totals_and_horizon |
| AC22 | Given Model W, when `project` is called with no arguments, then the result has horizon years 5, end_date "2031-10-06", granularity "annual" and 6 rows "2026" to "2031"; `granularity="monthly", horizon_years=10` gives 121 rows; `horizon_years` 0, 51 or 2.5 each error naming horizon_years and "1 to 50"; `granularity="weekly"` errors listing "monthly, quarterly, annual"; `granularity="monthly", horizon_years=11` errors naming granularity and "10 years" and suggesting quarterly or annual. Given an empty model, `project` errors saying the model has no accounts and naming `set_account`. | R14, R16 | integration | test_AC22_project_defaults_and_argument_checks |
| AC23 | Given Checking (asset, 1000) and no flows, when projecting 1 year annual with `in_todays_money`, then rows are 993.06 (2026, 86 days: 1000 / 1.03^(86/365.25)) and 970.89 (2027, 365 days), the summary end_balance is 970.89, and the result states values "todays_money" and inflation_rate 0.03; without the flag both rows are 1000.00. When `set_inflation_rate(rate=0.025)` is called, then the result is {inflation_rate 0.025, previous 0.03}; when `set_inflation_rate(rate=3)` is called, then it errors with a hint containing "0.03" and the rate stays 0.025; after `set_inflation_rate(rate=0)`, today's money rows equal nominal rows. Allowed: greater than -1 and less than 1. | R6, R15, R16 | integration | test_AC23_todays_money_and_inflation_rate |
| AC24 | Given 25 accounts with growth_rate 0.05 and 25 monthly fixed flows between them, when `project` runs with horizon_years 30 and granularity quarterly, then it returns in under 1 second wall-clock. | R18 | integration | test_AC24_thirty_year_projection_under_one_second |
| AC25 | Given the server started as a subprocess over stdio with logging at INFO, when Model W is built through `set_account` and `set_flow` and `show_model` and `project` are called, then every line on stdout parses as a JSON-RPC message, and stderr contains none of "Checking", "Salary", "Car loan", "4000". | R19 | integration | test_AC25_stdout_is_mcp_only_and_logs_carry_no_financial_values |
| AC26 | Given a model file holding Checking (asset, 0.125), when `show_model` is called, then Checking's balance is 0.13 and net_worth_today is 0.13 (half up; half-even would give 0.12). | R7 | integration | test_AC26_money_rounds_half_up_to_cents |
| AC27 | Given an empty model, when `set_account(name="Big", kind="asset", balance=1000000000001)` or `set_account(name="Big", kind="asset", balance=-1000000000001)` is called, then each returns a tool error naming balance and the file is unchanged (it still does not exist). Given Model W, when `set_flow(name="Huge", to="Checking", amount=1000000000001, frequency="monthly")` is called, then it errors naming amount and the file is unchanged. Given a model file holding Debt (liability, 1000000, growth_rate 1.0) and no flows, when `project(horizon_years=50)` is called, then it returns a tool error naming horizon_years (the amount owed reaches 1,000,000 x (13/12)^600, about 7.2 x 10^26, above 10^15) and the file is unchanged. | R2, R4, R14, R16 | integration | test_AC27_money_limits_and_unreportable_projections_are_tool_errors |
| AC28 | Given the model file holds the bytes `{"version": 1, "x": "\xe9"}` (not UTF-8), or has mode 000, or the model path is a directory, when `show_model` and `set_inflation_rate(rate=0.02)` are called, then each returns a tool error containing the model path and the file (or directory) is unchanged. | R1, R16 | integration | test_AC28_unreadable_model_file_is_a_tool_error_naming_the_path |
| AC29 | Given a model file holding Model W plus a top-level key `"comment": "note"`, when `show_model` is called, then it returns a tool error containing the path and "comment". Given a model file in which Checking's object repeats the key `"balance"`, when `show_model` is called, then it returns a tool error containing the path and "balance". In both cases the file is unchanged. | R1 | integration | test_AC29_unknown_and_duplicate_keys_do_not_match_the_shape |
| AC30 | Given `<tmp>/link/model.json` is a symlink to `<tmp>/synced/model.json`, which holds Model W, and `WHATIF_MODEL_PATH` is the link, when `set_inflation_rate(rate=0.02)` is called, then the link is still a symlink to the same target and the target's JSON has inflation_rate 0.02. | R1 | integration | test_AC30_write_through_a_symlink_replaces_the_target |
| AC31 | Given HOME is a temp dir: with `WHATIF_MODEL_PATH="~/fin/model.json"`, `show_model` returns model_path `<HOME>/fin/model.json`; with `WHATIF_MODEL_PATH=""`, it returns `<HOME>/.whatif/model.json`; with `WHATIF_MODEL_PATH="model.json"`, `show_model` returns a tool error naming WHATIF_MODEL_PATH and nothing is created. Given `WHATIF_MODEL_PATH` is `<tmp>/a/b/model.json` (no `a`), when `set_account(name="Checking", kind="asset", balance=1)` succeeds, then `<tmp>/a` and `<tmp>/a/b` have mode 0700 and the file mode 0600. | R1 | integration | test_AC31_model_path_forms_and_created_directory_modes |
| AC32 | Given Checking (asset, 30.03) and Phone (from Checking, 10.01, monthly, start 2026-11-01, end 2027-01-01), when projecting 1 year monthly, then Checking's reaches_zero is "2027-01-01" and Checking is 0.00 in every row from 2027-01 (30.03 - 3 x 10.01 = 0, float residue about 3.6e-15). Given Holiday (asset, 0.3) and Spend (from Holiday, 0.1, monthly, start 2026-11-01, end 2027-01-01), then Holiday's reaches_zero is "2027-01-01" and no money value anywhere in the result is -0.0. | R13 | integration | test_AC32_reaches_zero_at_cents_and_no_negative_zero |
| AC33 | Given Model W, when `set_flow(name="Old", to="Checking", amount=1, frequency="weekly", start_date="1899-12-31")` is called, then it errors naming start_date and the file is unchanged; with `start_date="1900-01-01"` it succeeds. | R4, R16 | integration | test_AC33_start_date_on_or_after_1900 |
| AC34 | Given a model file holding Model W plus Gym (from Checking, 50, monthly, start_date "1899-12-31"), when `show_model` is called, then it returns a tool error containing the path and "start_date", and the file is unchanged. | R1, R4 | integration | test_AC34_file_flow_starting_before_1900_does_not_match_the_shape |

## Source behavior (only when porting or replacing existing code)
Source: the source engine (ADR 0004), its projection and recurrence code and their tests.

### Kept
- The recurrence frequencies, and calendar-month stepping with clamping to the month's last day.
- Occurrences strictly after today take effect; end_date is inclusive.
- A flow is a fixed amount or a rate of a referenced balance divided by fires per year, the
  balance read at the occurrence.
- Sign-aware double entry for assets and liabilities: borrowing raises a liability, paying lowers it.
- Same-date events applied in one fixed order (the source used rule creation order; here, the
  order flows were first added, with growth before flows).
- Today's money: `value / (1 + rate) ^ (max(0, days to the date) / 365.25)`.
- Net worth as assets minus liabilities; reaches_zero as the first crossing to at or below zero.
- The horizon stated in every result; default horizon 5 years and inflation 0.03.

### Dropped or fixed, and why
- Month-end drift (31 Jan -> 28 Feb -> 28 Mar ...): fixed, every step is anchored to the start day (R9).
- Semimonthly schedules that skipped months for start days after the 15th: fixed, twice every month (R9).
- Payments into a liability continuing past payoff, so the debt went negative and then grew at the
  loan's rate as if it were savings: capped at the amount owed (R11).
- Growth as a rate flow with its own frequency and start date: replaced by an account growth rate
  applied monthly on the 1st, effective annual for assets and APR for liabilities, and none at or
  below zero (R12). The rates mean what people quote: "7% return" and "6% APR".
- Default start date of 1 January of the current year: today instead, so a new flow never
  back-fires (R4).
- Horizon ending on the 1st of the month N years ahead, with a partial last period labelled as a
  full one: the horizon ends on today's date N years ahead and the last row says so (R13).
- Flow totals estimated as per-occurrence amount x frequency x horizon, ignoring start and end
  dates: replaced by exact totals of the occurrences that took effect (R13).
- Thinning a series to a handful of checkpoints: the caller picks granularity instead (R14).
- Fuzzy substring fallback when resolving names: names match exactly (R8).
- Income and expense ledger accounts: money from or to outside the model is an omitted `from` or
  `to` (R4).
- Tax withholding, rule value history (scheduled amount changes), plan-scoped name ambiguity,
  two-turn delete confirmation: out of scope (see Non-goals).
- Expected numbers come from hand-checked arithmetic, not recorded from the source engine (ADR 0004).

## Non-goals
- Tax withholding of any kind.
- Saved scenarios or plans; what-if (Spec 0002), solve-for (Spec 0003), bands (Spec 0004).
- Goals as separate entities; goal progress tracking.
- Stored projection settings (horizon or granularity) beyond the inflation rate.
- Flow amounts or rates that change on scheduled future dates. A future change is expressed as
  ending one flow and starting another.
- Balance history: only the current balance and the date it was set. Balances are treated as
  today's balances whatever their balance_as_of.
- Bank or CSV import.
- Cash-flow or spending-category reports.
- Weekly and semiannual granularity.
- Multiple models per file, or two servers writing the same file (ADR 0003).
- Undo, or confirmation before removal. The model file is the user's to back up.
- Recommendations of any kind.

## Constraints (perf, security, compliance, compatibility)
- ADR 0002: Python 3.12, `mcp` the only runtime dependency. ADR 0003: JSON file, atomic replace,
  mode 0600, version field, never overwritten when unreadable. ADR 0004: port, do not share;
  known defects fixed.
- Latency: under 1 s for a 30-year horizon on a model of about 50 accounts and flows (R18).
- "Today" is the local date at the time of each tool call; core takes it as an argument and tests
  fix it.
- stdout is reserved for MCP; logs on stderr without financial values above DEBUG.
- Output is numbers and stated assumptions, not advice. Money is reported rounded to cents; rates
  as given.

## Interfaces and data shapes
All tools are MCP tools over stdio. Dates are `YYYY-MM-DD`. Money in results is rounded to cents, half up;
internal values are not rounded between steps. Half up applies to the computed binary value, so a half
cent reached by float arithmetic may round down (3 x 0.075 shows 0.22). Errors are MCP tool results with `isError: true`
and a text message.

### Model file (version 1)
```json
{
  "version": 1,
  "inflation_rate": 0.03,
  "accounts": [
    {"name": "Checking", "kind": "asset", "balance": 5000.0, "balance_as_of": "2026-10-06",
     "growth_rate": 0.0, "volatility": 0.0}
  ],
  "flows": [
    {"name": "Salary", "from": null, "to": "Checking", "amount": 4000.0, "rate": null,
     "rate_of": null, "frequency": "monthly", "start_date": "2026-11-01", "end_date": null}
  ]
}
```
Flow order in the file is the order flows were first added (R12); an update or rename keeps a
flow's place. How flows refer to accounts in the file (name or internal id) is an implementation
choice, provided a rename keeps them attached.

### Tools
| Tool | Arguments | Result |
|------|-----------|--------|
| `set_account` | `name` (str, required); `kind` (`asset`/`liability`, required when new); `balance` (number, required when new); `growth_rate` (number, default 0); `volatility` (number, default 0); `new_name` (str) | `{created, account, previous?}` |
| `remove_account` | `name` | `{removed: account}` |
| `set_flow` | `name` (required); `from`, `to` (account name or null); `amount` or (`rate`, `rate_of`); `frequency` (required when new); `start_date` (default today); `end_date`; `new_name` | `{created, flow, previous?, similar_flows: [names]}` |
| `remove_flow` | `name` | `{removed: flow}` |
| `set_inflation_rate` | `rate` | `{inflation_rate, previous}` |
| `show_model` | none | `{model_path, today, inflation_rate, net_worth_today, accounts: [...], flows: [...]}` |
| `project` | `horizon_years` (int, default 5); `granularity` (default `annual`); `in_todays_money` (bool, default false) | see below |

`previous` holds the changed fields' earlier values and is present only on update.

### `project` result
```json
{
  "today": "2026-10-06",
  "horizon": {"years": 3, "from": "2026", "to": "2029", "end_date": "2029-10-06"},
  "granularity": "annual",
  "values": "nominal",
  "periods": [
    {"period": "2026", "end_date": "2026-12-31", "net_worth": 0.0,
     "balances": {"Checking": 0.0, "Savings": 0.0, "Car loan": 0.0}}
  ],
  "accounts": [
    {"name": "Car loan", "kind": "liability", "start_balance": 10000.0, "end_balance": 0.0,
     "reaches_zero": "2028-08-01", "growth_total": 562.51}
  ],
  "flows": [{"name": "Car payment", "total": 10562.51}]
}
```
`values` is `nominal` or `todays_money`; `inflation_rate` is present only for `todays_money`.
Period labels: monthly `YYYY-MM`, quarterly `YYYY-Qn`, annual `YYYY`. `reaches_zero` is the first
date after today on which the balance, after that date's events, is at or below zero having been
above zero; null otherwise. `growth_total` is the sum of growth applied over the horizon (returns
for assets, interest for liabilities). The `periods` row values shown are placeholders.

## Edge cases and failure modes
- Occurrence on today: ignored. A one_time flow on or before today is refused at `set_flow` (it
  would never fire); an existing one_time flow whose date has since passed is kept and no longer
  fires.
- Start day 29, 30 or 31: clamped per month, never drifting. Leap-day annual start: 28 Feb in
  common years, 29 Feb in leap years.
- Today is 29 Feb: the horizon end clamps to 28 Feb N years later when that year has no 29 Feb.
- end_date equal to start_date: one occurrence.
- Flow whose end_date is before today: kept, contributes nothing.
- Liability overpayment: capped; a liability at 0 receives nothing and accrues nothing.
- Asset below zero: allowed, earns no growth, shown by reaches_zero.
- rate_of an account at or below zero: the rate flow moves nothing.
- Rate flow into a liability: computed, then capped like any payment.
- Negative growth_rate (greater than -1): an asset shrinks; growth_total is negative.
- Account referenced by a flow: cannot be removed until the flow is removed or changed.
- Rename collision, including case-only differences against another account: refused. Renaming
  to the same name with different case: allowed.
- Corrupt or wrong-version file: every tool errors, file untouched. Write interrupted: previous
  file intact.
- Empty model: `project` errors naming `set_account`.
- Monthly granularity beyond 10 years: refused with a hint, which keeps results to at most 121 rows.

## Open questions (must be empty before approval)
| # | Question | Proposed answer | AC that depend on it |
|---|----------|-----------------|----------------------|
