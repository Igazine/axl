---
name: axl-init
description: "Initializes AXL (Agent eXchange Language) for a project. Loads the spec, reads or creates the project .axl file, and activates persistent state saving behavior for the session. Invoke as: axl-init [filename.axl] — defaults to project.axl if no filename given."
---

# AXL Init

## Step 1 — Resolve the target file

The user may invoke this skill as:
- `axl-init` — use `project.axl` in the current directory
- `axl-init myproject.axl` — use the given filename
- `axl-init path/to/myproject.axl` — use the given path

Extract the filename or path from the invocation. If none was given, default to `project.axl`. Store this path — every subsequent read and write in this session targets this file.

## Step 2 — Load the AXL specification

Read the file `axl.spec` located in the same directory as this skill file. Read it in full before doing anything else.

Internalize all blocks, syntax rules, value types, status tokens, and — critically — Section 0 (Common Mistakes). Do not summarize or skim. The spec is the source of truth for everything that follows.

## Step 3 — Load or create the project file

**If the target file exists:** read it in full. Parse all blocks. Check `@meta.v` — if it does not match the spec version you just loaded (0.3), note it and plan to update it on the first write. Do not treat the file's existing version as the format authority; the spec you loaded in Step 2 is always authoritative. Resume from `@state.focus` and `@state.next_act`. Note any active blockers in `@state.blockers`. Check `@done-ctx` for already-executed one-time directives.

**If the target file does not exist:** create it using the template below. Ask the user for the project name and a brief description before creating. Infer `@plan` tasks and `@ctx` rules from the description if possible, or leave them minimal and let the user fill them in.

### New file template

```
@meta
id: {project-slug}
v: 0.3
name: {Project Name}
created: {current datetime as @YYYYMMDDTHHMM}
modified: {current datetime as @YYYYMMDDTHHMM}
agents: {your model id}
tags: ~

@state
status: TODO
focus: project initialization
phase: ~
blockers: ~
last_act: ~
next_act: define initial tasks in @plan
err: ~
>>mem

@plan

@ctx

@log

@ref
```

## Step 4 — Confirm initialization

Report back to the user in one short paragraph:
- Which file was loaded or created
- Current `@state.status` and `@state.focus`
- The next recommended action (`@state.next_act`)
- How many tasks are in `@plan` and how many are WIP or BLOCK

## Step 5 — Activate persistent save behavior

From this point forward, for the remainder of this session, apply all of the following rules automatically — without waiting to be asked:

**After every meaningful action:**
- Update `@state.focus`, `@state.last_act`, and `@state.next_act`
- Update any relevant `@plan` task STATUS in-place
- Append a structured entry to `@log` using the format: `@YYYYMMDDTHHMM:model-id:PREFIX:entry text`
  - Use `ACT:` for completed actions
  - Use `ERR:` for errors or failures
  - Use `NOTE:` for decisions or observations
  - Use `WARN:` for non-fatal issues
- Set `@meta.modified` to the current datetime (`@YYYYMMDDTHHMM`) — never write literal `!NOW` to disk
- If you have a session ID, write or update your entry in `@meta>>sessions` (format: `your-model-id: session-id`). Only write your own entry. Check the following environment variables in order and use the first available value:
  - Codex CLI: `$CODEX_THREAD_ID`
  - Claude Code: `$CLAUDE_SESSION_ID`, fallback `$TERM_SESSION_ID`
  - Any CLI on macOS: `$TERM_SESSION_ID`
  - If none available: omit the entry entirely — never write a placeholder or generated value
- Write the updated file to disk

**After completing any @plan task:**
- Set its STATUS to `DONE`
- Set `@state.next_act` to the next highest-priority `TODO` or `WIP` task
- Append an `ACT:` log entry naming the completed task
- Write the file

**After reaching a milestone (M_ task):**
- Set milestone STATUS to `DONE`
- Append a `NOTE:` log entry summarizing what the milestone covered
- Update `@state.phase` if the milestone marks a phase boundary
- Write the file

**When a blocker is encountered:**
- Set the affected task STATUS to `BLOCK` with a notes field naming the blocker
- Add the blocker to `@state.blockers`
- Set `@state.status` to `BLOCK` if the blocker is P0
- Append an `ERR:` or `WARN:` log entry
- Write the file

**When a session is ending (user says goodbye, done, stop, or similar):**
- Set `@state.next_act` to the clearest possible resumption point
- Append a `NOTE:` log entry summarizing the session's actions
- Write the file

**Write rules — always enforce:**
- Never write `!NOW` to disk — always replace with the actual current datetime
- Never delete or reorder `@plan` tasks — update STATUS in-place only
- Never delete `@log` entries — append only
- Never store secret values inline — use `*ENV_VAR_NAME` references only
- Never wrap `.axl` content in markdown fences

## Step 6 — Proceed

Resume or begin work. The project file is now active. All state changes will be persisted automatically.
