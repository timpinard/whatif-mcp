# Glossary
| Term | Definition | Do not confuse with |
|------|------------|---------------------|
| Model | Everything the user has described: accounts, flows and the inflation rate. One per model file. | Scenario (none in v1) |
| Account | Something with a balance: an asset (cash, investments, property) or a liability (loan, card). | Ledger account in the source engine (ADR 0004), which also covered income and expense |
| Balance | An account's value as of a date. Liabilities are stored as positive amounts owed. | Net worth |
| Outside | The side of a flow that is not an account in the model: where income comes from, where spending goes. | An account |
| Flow | A recurring movement of money: from outside, an account or outside, to another. Fixed amount or a rate of an account's balance. | Rule in the source engine (same idea, different name); Growth |
| Frequency | How often a flow fires: weekly, biweekly, semimonthly, monthly, quarterly, semiannual, annual, one_time. | Period |
| Occurrence | One date a flow fires on, and the amount moved that day. | Period |
| Growth rate | An account's own annual rate. Assets: effective annual return. Liabilities: APR, accrued monthly at rate/12. | A rate flow; Inflation rate |
| Growth total | The sum an account gained (asset) or accrued (liability) from its growth rate over a projection. | Net change in balance |
| Volatility | Standard deviation of an account's yearly growth rate, used only for bands. | Growth rate |
| Inflation rate | The model's annual rate used to convert to today's money. | Growth rate |
| Projection | Balances computed forward from today to the horizon, per period. | Forecast of actual spending |
| Horizon | How far a projection runs, in years. | Period |
| Period | One reporting step of a projection: a month, quarter or year (the granularity). | Frequency |
| Net worth | Sum of assets minus sum of liabilities at a point in time. | Balance |
| Reaches zero | The first date an account's balance is at or below zero in a projection; for a liability, its payoff date. | |
| Today's money | Values deflated by the inflation rate back to today. | Nominal |
| Baseline | The projection of the model as it is. | |
| Change | One hypothetical edit to the model, using the arguments of an editing tool. | Saved edit |
| What-if | A baseline compared with the same model plus a list of changes. Never saved. | Scenario |
| Solve-for | Finding the fixed amount of one flow that makes a target reach a value by a date. | What-if |
| Target | What a solve-for aims at: one account's balance, or net worth. | |
| Band | Percentile range (10th-90th) from Monte Carlo runs over accounts with volatility. | |
