# AXL — Agent eXchange Language

**A compact, machine-primary notation for cross-session, cross-agent state and instructions.**

AXL is a lightweight text format designed to be loaded by AI agents, LLMs, and orchestration harnesses as a persistent memory and instruction layer. It is not a replacement for Markdown — it is the layer underneath: a structured, token-efficient file format that agents read, update, and hand off between sessions without human intervention.

---

## Motivation

Most AI coding tools and agent harnesses recommend Markdown files for persisting project state, instructions, and memory across sessions. Markdown is excellent for human readability. It is not optimized for machine consumption — it is verbose, structurally ambiguous, and costly in tokens when included in context repeatedly.

AXL addresses this with a purpose-built format:

- **Token-efficient** — approximately 40% fewer tokens than equivalent structured Markdown
- **Machine-primary** — unambiguous structure; no prose parsing required
- **Self-describing** — a single `axl.spec` file is sufficient for any agent to read, write, and validate `.axl` files
- **Cross-agent** — designed for handoffs between different agents, models, and sessions
- **Human-legible** — a developer can glance at an `.axl` file and understand the project state; they just don't need to write it themselves

---

## How it works

Load the spec once. From that point on, any agent understands the format.

```
Load the AXL specification from ./axl.spec, then load ./my-project.axl.
Resume from the current state and continue work.
```

That's the entire integration surface. No libraries, no parsers, no schemas to install.

---

## File types

| Extension | Purpose |
|-----------|---------|
| `.axl` | Full project file — state, plan, instructions, log |
| `.axlp` | Patch file — sparse updates applied to a target `.axl` |
| `.axlt` | Type library — reusable field schemas, importable across projects |

---

## Format overview

An `.axl` file is composed of **blocks**. Each block begins with `@BLOCKNAME` and ends at the next block or end of file. Blocks contain typed key-value pairs, structured lists, and sub-sections.

```
@meta
id: my-project
v: 0.2
created: @20250510
modified: @20250510T1435
agents: claude-sonnet-4
tags: api|typescript

@state
status: WIP
focus: implementing authentication middleware
blockers: ~
next_act: add JWT verification to /api/* routes
>>mem
port: #3000
db_url: :postgres://localhost:5432/mydb

@plan
setup:DONE:P1:Initialize repository and toolchain
auth:WIP:P0:JWT authentication middleware
tests:TODO:P1:Integration test suite
M_mvp:TODO:~:MVP — core API functional

@ctx
> TypeScript strict mode; no implicit any
> write tests before marking any task DONE
? task:blocked => set @state.status BLOCK and halt

@log
@20250510T1400:claude-sonnet-4:ACT:repository initialized; dependencies installed
```

### Value types

AXL uses sigil prefixes to eliminate redundant type declarations:

| Sigil | Type | Example |
|-------|------|---------|
| _(none)_ | plain text | `key: some text` |
| `:` | URL | `key: :https://example.com` |
| `#` | number | `key: #42` |
| `?` | boolean | `key: ?1` |
| `@` | date/datetime | `key: @20250510T1435` |
| `$` | ID reference | `key: $other-task-id` |
| `*` | environment variable name | `key: *DATABASE_URL` |
| `~` | null / empty | `key: ~` |
| `!NOW` | computed timestamp | `key: !NOW` _(agent replaces on write)_ |

Pipe (`|`) separates list elements inline: `tags: api|typescript|postgres`

### Core blocks

| Block | Required | Description |
|-------|----------|-------------|
| `@meta` | yes | Project identity, version, modification tracking |
| `@state` | yes | Current session memory, focus, blockers, agent scratchpad (`>>mem`) |
| `@plan` | no | Task list in `id:STATUS:PRIORITY:title[:notes]` format |
| `@ctx` | no | Behavioral directives, conditional rules, one-time instructions |
| `@log` | yes | Append-only structured event log |
| `@done-ctx` | no | Append-only audit log of executed one-time `@ctx` directives |
| `@ref` | no | URLs, filesystem paths, environment variable names, glossary |

### Modularity blocks

| Block | Description |
|-------|-------------|
| `@import` | Read-only references to other `.axl` or `.axlt` files |
| `@mount` | Read-write references to shared `.axl` files (with `@lock` guard) |
| `@export` | Named symbols exposed to files that import this one |

### Extension blocks

| Block | Description |
|-------|-------------|
| `@hook` | Event-triggered directives (`task:done`, `session:end`, `err:raised`, …) |
| `@type` | Custom field schemas for `@state>>mem` validation |
| `@diff` | Sparse patch operations for `.axlp` files |
| `@fence` | Verbatim content blocks (system prompts, code snippets, templates) |
| `@lock` | Ephemeral concurrency guard for shared files |
| `@err` | Structured error and conflict log, separate from `@log` |
| `@logref` | External log file reference and rotation policy |
| `@prompt` | Compressed human instruction, produced by `axlc-mcp` |

> **Note on harness-specific config:** AXL deliberately has no block for harness instructions (Cursor rules, `CLAUDE.md`, Aider flags, etc.). Those belong in each harness's own native config files — they are read once at session start by one harness, so storing them in a shared project file would burn tokens on every context load for zero benefit to any other consumer. If you need a single source of truth that *generates* those native files, that's a separate tooling concern outside the AXL format.

---

## Task format

Tasks in `@plan` use colon-delimited fields:

```
id:STATUS:PRIORITY:title[:notes]
```

**Status tokens:** `TODO` `WAIT` `WIP` `DONE` `SKIP` `FAIL` `BLOCK` `REVIEW` `HOLD`

**Priority tokens:** `P0` (critical) `P1` (high) `P2` (normal) `P3` (low)

**Milestones** use `M_` prefix and omit priority: `M_beta:WIP:~:Beta release`

Tasks are grouped with `>>SECTIONNAME` lines. Agents update status in-place and never delete or reorder task lines.

---

## Directives in `@ctx`

```
>  DIRECTIVE           — always follow
?  CONDITION => ACTION — conditional; evaluated before each action
!  DIRECTIVE           — one-time; agent appends to @done-ctx on execution, then skips on repeat
-  NOTE                — informational; agent reads but does not act
```

One-time directives (`!`) are never mutated in `@ctx`. Instead, agents append the executed directive verbatim to `@done-ctx` with a timestamp and agent ID. On subsequent sessions, agents check `@done-ctx` before executing any `!` directive — if it's already there, it's skipped. This keeps `@ctx` immutable and makes one-time execution auditable.

Built-in condition tokens: `task:done` `task:blocked` `task:added` `state:changed` `session:start` `session:end` `file:written` `import:missing` `err:raised` `lock:conflict`

---

## Modularity

### Importing a file (read-only)

```
@import
team: ./team.axl::ref
types: ./project.axlt
```

Access imported content in this file with `$alias::block::item-id`. Missing imports write an `ERR:` entry to `@log` and continue — imports are non-fatal.

### Mounting a shared file (read-write)

```
@mount
shared: ./team-state.axl
```

Mounted files represent shared mutable state. Agents must check `@lock` before writing. On conflict, agents write to `@err` and await user resolution rather than overwriting.

### Exporting symbols

```
@export
api-version: #2
deploy-url: $state>>mem>>staging_url
```

Importers access these as `$their-alias::export::api-version`.

---

## Patch files (`.axlp`)

For large projects where only a few fields change per session, agents can write a sparse patch file instead of rewriting the full `.axl`:

```
@diff
target: ./project.axl
base_modified: @20250510T1435

STATUS  plan::stripe-wh: DONE
NOTE    plan::stripe-wh: HMAC fixed — secret was URL-encoded in Railway
STATUS  plan::stripe-refund: WIP
SET     state::focus: implementing refund endpoint
SET     meta::modified: !NOW
APPEND  log: !NOW:claude-sonnet-4:ACT:stripe-wh resolved; moving to refund
```

Patches are applied only when `base_modified` matches the target's current `modified` field, preventing stale overwrites.

---

## Verbatim content with `@fence`

Embed raw content that the parser should not interpret — system prompts, configuration fragments, code templates:

```
@fence sys-prompt txt
You are a senior backend engineer. Always use TypeScript strict mode.
Never use `any`. Prefer explicit return types on all functions.
@fence/sys-prompt
```

---

## Hooks

React to agent lifecycle events without relying on the agent remembering:

```
@hook
task:done    => > append ACT: entry to @log with task id and completion time
task:blocked => > set @state.status BLOCK and update @state.blockers
session:end  => > write NOTE: summary of all actions taken this session
err:raised   => > set @state.status BLOCK and halt further actions
```

---

## Token footprint

Approximate comparison for a mid-sized project file (18 tasks, current state, 10 log entries):

| Format | Tokens (approx.) |
|--------|-----------------|
| Equivalent structured Markdown | ~680 |
| AXL v0.1 | ~420 |
| AXL v0.2 | ~310 |

Savings increase with project size. `@state>>mem` and `@plan` are the highest-density sections; `@log` grows linearly but remains compact due to the colon-delimited format.

---

## Repository structure

```
axl.spec          # Canonical specification — the only file agents need to load
README.md         # This file
prompts.md        # Ready-to-use prompts for agents and harnesses
examples/
  project.axl     # Full example project file
  patch.axlp      # Example patch file
  types.axlt      # Example type library
  team.axl        # Example shared reference file
```

---

## Versioning

The current spec version is **0.2**. The version is declared in `@meta`:

```
@meta
v: 0.2
```

Agents parsing v0.1 files must accept the older pipe-delimited plan and log formats and must not silently upgrade format on rewrite unless explicitly instructed. Unknown blocks must always be preserved verbatim — forward compatibility is non-negotiable.

---

## Design principles

**Agents are the primary writers.** Humans define intent; agents maintain state. The format is optimized for machine generation and parsing, not human authoring.

**A single spec file is sufficient.** No runtime dependencies, no installed libraries. Any LLM that can read `axl.spec` can immediately produce valid `.axl` files.

**Append-only logs, in-place task updates.** `@log` and `@err` are append-only. `@plan` task statuses update in-place. Neither is ever deleted. This creates a reliable audit trail across sessions and agents.

**Secrets never appear as values.** Secret values are always referenced by environment variable name using the `*` sigil. `key: *DATABASE_URL` is valid. `key: postgres://user:pass@host/db` is not — use a `:url` sigil pointing to a non-secret URL, or store the credential name only.

**Unknown content is preserved.** Agents must pass through any block or field they do not recognize. This ensures files written by future spec versions remain intact when processed by agents trained on earlier versions.

---

## Prompt Examples

Open [prompts.md](prompts.md) for ready-to-use prompts for loading AXL into agents, coding assistants, and orchestration harnesses

---

## License

MIT
