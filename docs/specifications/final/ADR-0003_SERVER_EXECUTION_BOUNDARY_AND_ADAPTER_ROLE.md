# ADR: Server Execution Boundary and Adapter Role

Date: 2026-02-18
Status: Accepted

## Context

ScratchBird execution architecture has one engine execution boundary and a separate parser/wire adapter layer.

Validated implementation references in `ScratchBird`:

- `src/server/server_session.cpp` handles the server execution path.
- `src/protocol/adapters/native_adapter.cpp` is protocol/parser translation, not an engine execution path.
- `src/protocol/adapters/protocol_adapter.cpp` performs compiler selection for SQL->SBLR translation in adapter flow.

## Decision

Adopt the following operational rules for all `ScratchBird-ai` integration work:

1. Single engine execution boundary:
- Treat `ServerSession` as the only engine execution path.
- Do not introduce additional SQL execution paths in server/executor code.

2. Adapter role:
- Treat `native_adapter` as parser/wire translation and protocol/session state handling.
- Compilation in adapter paths is allowed; engine execution remains in `ServerSession`.

3. SQL handling rule:
- SQL text must be compiled to SBLR before engine submission.
- Engine execution layer must only execute validated SBLR/internal procedures.

4. Listener/parser/driver rule:
- One dialect parser per configured port.
- No protocol auto-detect fallback in parser logic.

## Consequences

Positive:

- Preserves strict parser/engine separation.
- Avoids accidental dual execution semantics.
- Keeps driver/parser behavior aligned with engine invariants.

Negative:

- Requires explicit per-port parser/listener configuration.
- Requires adapter/path reviews when parser teams evolve protocol behavior.

## Follow-up Actions

- Keep `ScratchBird-ai` bridge/adapter docs explicit that SQL goes to parser/wire layer and engine receives SBLR.
- Reject any `ScratchBird-ai` change proposal that implies direct SQL execution in server/executor.
