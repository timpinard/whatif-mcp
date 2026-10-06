# Glossary
| Term | Definition | Do not confuse with |
|------|------------|---------------------|
| Model | Everything the user has described: accounts, flows, settings. One per model file. | Scenario (none in v1) |
| Account | Something with a balance: an asset (cash, investments, property) or a liability (loan, card). | Ledger account in the source project, which also covered income and expense |
| Balance | An account's value as of a date. Liabilities are stored as positive amounts owed. | Net worth |
| Flow | A recurring movement of money: into an account, out of it, or between two. Fixed amount or a rate of a balance. | Rule in the source project (same idea, different name) |
| Growth | A flow that adds a rate of an account's own balance to it: returns, interest charged. | Inflation |
| Projection | Balances computed forward from today to the horizon, per period. | Forecast of actual spending |
| Horizon | How far a projection runs, in years. | Period |
| Period | One reporting step of a projection: a month, quarter or year (the granularity). | Frequency of a flow |
| Net worth | Sum of assets minus sum of liabilities at a point in time. | Balance |
| Today's money | Values deflated by the model's inflation rate back to today. | Nominal |
| Baseline | The projection of the model as it is. | |
| Change | One hypothetical edit to the model: add, remove or alter a flow, or alter a balance. | Saved edit |
| What-if | A baseline compared with the same model plus a list of changes. Never saved. | Scenario |
| Band | Percentile range (e.g. 10th-90th) from Monte Carlo runs over volatile accounts. | |
