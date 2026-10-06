# ADR 0003: Keep the model in a local JSON file
- Status: proposed
- Date: 2026-10-06
- Deciders: Timothy Pinard

## Context
Tools build the model up over a conversation, so state must persist between calls and sessions.
The data is personal and the tool runs on the user's machine.

## Decision
One JSON file per model, default `~/.whatif/model.json`, path overridable by environment
variable. Every write replaces the file atomically (write temp file, then rename), created with
mode 0600. The file carries a `version` field so the format can change later.

## Consequences
- The user owns, can read, back up and delete their data with ordinary tools.
- One writer at a time is assumed; two servers on the same file can lose a write.
- No query capability: the whole model is loaded per call. Fine at personal scale.

## Alternatives considered
- Stateless tools (the whole model passed on every call): no storage, but the assistant must
  resend every account with every question.
- SQLite: queryable and transactional, but opaque to the user and unnecessary at this size.
