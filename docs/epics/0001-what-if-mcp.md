# Epic 0001: What-if answers about my own money, inside my AI assistant
- Status: approved
- Product owner: Timothy Pinard
- Jira: (not yet created)
- Note: reconstructed on 2026-10-06 from the owner's request and Specs 0001-0004, after the specs
  were written. In the process this document comes first and the specs are derived from it.

## Problem
People make money decisions by asking "what if": save more, pay a loan off faster, take a pay cut,
spend on something big. Planning apps that answer this need an hour of setup and usually a
subscription. Bank apps hold the real balances but only look backwards. AI assistants are
where people now ask these questions, but an assistant answering from its own head produces
plausible numbers that nobody can check.

## Outcome
"I told my assistant what I have and what comes in and goes out. Now I can ask what happens if I
change something and get an answer with real numbers I can trust, in a few seconds, without my
data leaving my machine."

## Users
One person managing their own household finances, already using an AI assistant that supports
MCP (desktop or command line). Comfortable describing their finances in conversation; not willing
to fill in spreadsheets.

## Success measures
- A typical household (5-10 accounts and flows) is described in one conversation, under 10
  minutes.
- Every number in an answer is reproducible by hand from the stated model and assumptions.
- Every what-if leaves the user's saved model exactly as it was.
- An answer arrives within a normal assistant turn (about a second without uncertainty bands).
- The user can find, read and delete their data with ordinary tools.

## Scope (capabilities, each becomes one spec and one story)
| Capability | Spec | Story | Priority |
|------------|------|-------|----------|
| Describe my finances and see where they lead | Spec 0001 | | Must |
| Compare "as is" with "what if I changed..." | Spec 0002 | | Must |
| Work backwards: "how much a month to reach X by Y?" | Spec 0003 | | Should |
| See how wide the outcome could be for investments | Spec 0004 | | Could |

## Out of scope
- Advice or recommendations: answers state numbers and assumptions only.
- Taxes, including withholding.
- Connecting to banks or importing statements (a later epic: CSV, then bank feeds).
- Saved scenarios, goals, budgets, multiple people or households.
- Any hosted service, account or sign-in.

## Assumptions and risks
- Assumes users will describe their finances in conversation accurately enough for the answer to
  matter. Risk: a wrong input produces a confident wrong answer; mitigated by showing the model
  back and stating assumptions in every answer.
- Assumes MCP clients stay the way people reach assistants on their own machine.
- Risk: uncertainty bands may be too slow without a numerical library (ADR 0002, Spec 0004).
- Risk: results read as advice. Mitigated by wording rules in every spec.

## Epic acceptance (a walkthrough a non-engineer could run)
1. In the assistant: "I have $5,000 in checking, a $10,000 car loan at 6% that I pay $500 a month,
   and I'm paid $4,000 a month." The assistant shows the model back correctly.
2. "Where will I be in three years?" Net worth by year, and the car loan's payoff date.
3. "What if I paid $1,000 a month on the loan?" An earlier payoff date and the interest saved,
   and the saved model is unchanged afterwards.
4. "What car payment clears the loan by next October?" One amount, to the cent.
5. Open the model file: it is readable, and deleting it leaves no other trace.
