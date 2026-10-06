# Architecture

## System overview
```
AI assistant (Claude Desktop, Claude Code, ...)
      |  MCP over stdio
      v
server  - MCP tool definitions; validates arguments, calls store + core, shapes results
      |
      +--> store - loads and saves the model file
      +--> core  - pure projection math over in-memory data
```

## Components and boundaries
- `whatif_mcp.core`: pure functions over dataclasses. No I/O, no clock reads: "today" is an
  argument. Everything numeric lives here and is unit tested here.
- `whatif_mcp.store`: reads and writes the model file. The only module that touches disk.
- `whatif_mcp.server`: the MCP surface. Thin: argument validation, name resolution, calls
  into store and core, result shaping. No projection math.
- Dependencies point one way: server -> store, server -> core. core imports nothing from the
  other two.

## Runtime inputs (clock, environment variables, config files)
- The server reads today's date from the system clock once per call and passes it into core.
- `WHATIF_MODEL_PATH`: model file path (ADR 0003).

## Data stores
- One JSON file per model, default `~/.whatif/model.json`, overridable by environment
  variable. Written atomically (temp file + rename). See ADR 0003.

## External integrations
- MCP clients over stdio. No network calls, no telemetry.

## Known constraints (perf, compliance, security)
- stdout is the MCP transport: nothing else may write to it. Logs go to stderr.
- `project` without bands returns in under 1 s for a 30-year horizon on a model of ~50 accounts
  and flows. The bands budget is set in the bands spec.
- Output is projection, not advice: results state numbers and assumptions, never
  recommendations.
- The model file holds personal financial data: it is created user-readable only (0600).
