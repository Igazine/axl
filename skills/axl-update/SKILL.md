---
name: axl-update
description: Explicitly saves the current session state to the active AXL project file. Use when you want a guaranteed write regardless of automatic save behavior — after a significant action, before ending a session, or when working with a model that doesn't reliably auto-save. Requires `axl-init` to have been run first in this session. Optionally accepts a summary `axl-update "completed auth module"`.
---

# AXL Update

## Prerequisites

This skill requires `axl-init` to have been run earlier in this session. The target `.axl` file path must already be established. If it is not, run `axl-init [filename.axl]` first.

If you are uncertain which file is active, ask the user before proceeding.

## Step 1 — Resolve the update summary

The user may invoke this skill as:
- `axl-update` — infer the summary from recent conversation context
- `axl-update "completed auth module, starting payments"` — use the given summary as the `last_act` value and for the log entry

If no summary is given, review the last few exchanges in the conversation and infer: what was just completed or decided? Use that as the summary. If nothing meaningful happened since the last write, note that and skip the write — do not create empty log entries.

## Step 2 — Collect current state

Before writing, assess the current state of the session:

- **Focus:** what is being worked on right now?
- **Last action:** what was most recently completed?
- **Next action:** what is the clearest next step?
- **Blockers:** anything blocking progress? (or `~` if none)
- **Task updates:** have any `@plan` tasks changed status since the last write?
- **Errors or warnings:** anything that went wrong or was noted?

## Step 3 — Write the update

Apply the following operations to the active `.axl` file:

**Always update:**
```
@state.focus        ← current focus
@state.last_act     ← ACT: + summary of what was just done
@state.next_act     ← clearest next step
@state.blockers     ← current blockers, or ~
@state.err          ← current error if any, or ~
@meta.modified      ← current datetime as @YYYYMMDDTHHMM (never !NOW)
```

**Update if changed:**
```
@plan task STATUSes ← any tasks that moved to WIP / DONE / BLOCK / etc.
@state.phase        ← if a phase boundary was crossed
@state>>mem keys    ← any memory values that changed
```

**Always append to @log:**
```
@YYYYMMDDTHHMM:{model-id}:{PREFIX}:{summary}
```

Use `ACT:` if work was completed, `NOTE:` if a decision was made, `WARN:` if something was flagged, `ERR:` if something failed.

**If a one-time `@ctx` directive was executed:**
```
Append to @done-ctx: @YYYYMMDDTHHMM:{model-id}:{directive text verbatim}
Do NOT modify the @ctx source line.
```

## Step 4 — Enforce write rules

Before saving, verify:

- [ ] No `!NOW` anywhere in the file — all replaced with `@YYYYMMDDTHHMM`
- [ ] No `@plan` tasks deleted or reordered — STATUS updated in-place only
- [ ] No `@log` entries deleted — new entry appended only
- [ ] No secret values stored inline — `*ENV_VAR_NAME` references only
- [ ] No markdown fences wrapping the file content

## Step 5 — Confirm

After writing, confirm to the user in one line:
- What was saved
- The file path
- The current `@state.status`

Example: `Saved to project.axl — status: WIP, focus: payment integration, 2 tasks updated.`

Then continue with whatever comes next. Do not pause for acknowledgment unless the write failed.

## When to use axl-update manually

`axl-init` instructs automatic saving after every meaningful action. Use `axl-update` explicitly when:

- You want a guaranteed checkpoint before a risky operation
- The model has been running for a long time and you're unsure if auto-saves fired
- You're about to end the session and want a clean final state
- You switched tasks abruptly and want to lock in the previous task's state
- You're using a smaller model that may not auto-save reliably
