# Jira mapping
The docs are the source of truth; Jira tracks status and ownership. Descriptions in Jira summarize
and point to the doc; they are not edited in Jira. Issue keys are recorded in each doc's header.

## Issue types
| SDD artifact | Jira issue | Created when | Created by | Description holds |
|--------------|-----------|--------------|------------|-------------------|
| Epic doc (docs/epics/) | Epic | Epic approved | PO | Problem, Outcome, Success measures, Out of scope; link to the doc |
| Spec (docs/specs/) | Story, child of the epic | Spec drafted | ticket-agent (draft), PO + Eng approve | Intent, AC table as a checklist; link to the spec |
| Task row (docs/tasks/) | Sub-task of the story | Plan approved | planner | Task title, AC covered, depends on; link to the tasks doc |
| QA finding beyond the AC | Bug, linked to the story | qa-agent report | qa-agent proposes, Eng confirms | Repro and the proposed spec amendment |
| Escaped defect | Bug, label `escaped` | Found after merge | Anyone | Repro; feeds the escape rate in metrics |
| ADR | none (linked from the epic) | - | - | - |

## Status transitions driven by gates
| Jira transition | Issue | Triggered by |
|-----------------|-------|--------------|
| Draft -> Ready | Story | Spec Status: approved (human gate) |
| Ready -> Planned | Story | Plan Status: approved (human gate); sub-tasks created |
| To do -> In progress | Sub-task | Implementer cuts branch task/NNNN-Tn-name |
| In progress -> In review | Sub-task | Gates green; review file written |
| In review -> In progress | Sub-task | Review findings: regeneration count +1 |
| In review -> Done | Sub-task | Human merge gate |
| Planned -> Done | Story | Last sub-task merged; spec Status: implemented |
| -> Done | Epic | All Must stories done; epic acceptance walkthrough passed |

## Fields carried from metrics/log.csv
first_pass, regenerations, review findings (agent and human) and cycle time are recorded per
sub-task; escapes per story.

## Not yet decided
- Whether agents write to Jira directly (needs a Jira connection) or a human mirrors the changes.
- Where Jira keys go given AGENTS.md rule 7 (proposed: a `Jira:` header line is allowed in epics,
  specs, plans and tasks).
