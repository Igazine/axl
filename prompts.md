# AXL Prompts

Ready-to-use prompts for loading AXL into agents, coding assistants, and orchestration harnesses. Copy, fill in the path placeholders, and send.

All prompts assume the agent has access to the filesystem at the given paths. Adjust path syntax for your environment (absolute vs. relative, Windows vs. Unix).

---

## Guardrail prompt (prepend to any session when using smaller models)

Smaller models (under 7B) may drift from spec constraints over a long session,
especially on `!NOW` resolution and append-only rules. Prepend this to your
session-start prompt when using a local model in CLI chat. It front-loads the
highest-risk rules in plain, direct language before any AXL work begins.

```
Before doing anything with AXL files, memorize these rules — they override
any other interpretation you might have:

1. NEVER write !NOW to any file. Always replace it with the actual current
   datetime in @YYYYMMDDTHHMM format (e.g. @20250510T1435). !NOW is a
   placeholder for prompts only. It is invalid on disk.

2. NEVER delete, reorder, or truncate @plan tasks or @log entries.
   Update task STATUS in-place. Append to @log. Rotate via @logref if large.

3. NEVER store secret values in .axl files. Use *ENV_VAR_NAME (the name
   only) to reference environment variables.

4. NEVER wrap .axl output in markdown code fences. Plain text only.

5. NEVER modify @ctx lines. Record executed one-time (!) directives in
   @done-ctx instead, leaving @ctx unchanged.

Confirm you have memorized these rules before proceeding.
```

---

## Standard session start

The most common prompt. Loads the spec and a project file, then resumes work from the last known state.

```
Load the AXL specification from {path/to/axl.spec} and read it in full.
Then load {path/to/project.axl}, parse all blocks, and resume from the current state.

Continue from @state.next_act. If that field is empty, continue the highest-priority
WIP task in @plan. If no WIP tasks exist, ask me which TODO task to begin.

After each meaningful action, update @state, the relevant @plan task statuses,
and append a structured entry to @log. Write the updated file to disk before
ending the session.
```

---

## Read-only status review

Loads and summarizes a project file without making any changes. Useful for status checks, planning, or onboarding a new agent to an existing project.

```
Load the AXL specification from {path/to/axl.spec}.
Then load {path/to/project.axl} in read-only mode — do not write any changes.

Provide a concise summary covering:
- Overall project status (@state.status and @state.phase)
- Current focus and what was last completed
- Active blockers, if any
- The next recommended action
- A brief @log digest: last 5 entries

Do not expand the AXL content into prose. Summarize only.
```

---

## New project bootstrap

Creates a new `.axl` file from a plain-language project description. Asks for confirmation before writing to disk.

```
Load the AXL specification from {path/to/axl.spec}.

Create a new AXL project file at {path/to/new-project.axl} for the following:

---
{Describe your project here. Include: what it is, the main goals, the technology
stack if known, and any immediate tasks or milestones you have in mind.}
---

Populate @meta, @state, @plan (with realistic tasks, statuses, and priorities),
and @ctx (with any stack or workflow directives you can infer from the description).
Leave @log empty — the first entry will be written on first action.

Show me the complete file content before writing. Ask for confirmation first.
```

---

## Agent handoff

Used when a new agent (or a new session of the same agent) is taking over an in-progress project. Orients the incoming agent before proceeding.

```
Load the AXL specification from {path/to/axl.spec}.
Then load {path/to/project.axl}.

You are taking over from a previous agent. Before doing anything:

1. Read @log in full to understand the history of actions taken.
2. Read @state.focus, @state.last_act, and @state.next_act.
3. Note any active blockers in @state.blockers.
4. Identify the current WIP task in @plan and its notes.

Summarize your understanding of where the project stands in two or three sentences,
then ask me how you should proceed — or proceed directly if @state.next_act is
unambiguous.

Add yourself to @meta.agents on your first write.
```

---

## Apply a patch file

Instructs an agent to apply a `.axlp` sparse patch to a target project file.

```
Load the AXL specification from {path/to/axl.spec}.

Apply the patch file at {path/to/patch.axlp} to {path/to/project.axl}.

Before applying:
- Verify that the patch's base_modified field matches the target file's @meta.modified.
- If they do not match, do not apply. Write a CONFLICT entry to @err and report to me.

After a successful apply:
- Confirm which operations were applied.
- Report the updated @state.status and @state.focus.
```

---

## Migrate from v0.1 to v0.2

Upgrades a v0.1-format file to the current v0.2 format. Always ask for confirmation before writing.

```
Load the AXL specification from {path/to/axl.spec}.
Then load {path/to/old-project.axl}.

This file uses AXL v0.1 format. Migrate it to v0.2:

- Convert pipe-delimited @plan lines to colon-delimited format
- Convert vars.KEY entries in @state to >>mem KEY entries
- Convert pipe-delimited @log lines to @DATETIME:AGENT:PREFIX:text format
- Add ACT/ERR/NOTE/WARN prefixes to @log entries where the type is clear;
  use NOTE as the default prefix where ambiguous
- Update @meta.v to 0.2
- Do not change any content, statuses, task titles, or log text — format only

Show me a diff or the complete converted file before writing. Ask for confirmation.
```

---

## Load with type library

For projects using an `.axlt` type library, this prompt ensures the agent loads and validates against it.

```
Load the AXL specification from {path/to/axl.spec}.
Load the type library from {path/to/types.axlt}.
Then load {path/to/project.axl}.

Apply the type definitions from the library when reading and writing @state>>mem values.
If any existing mem values violate their declared type constraints, report them as
CONSTRAINT entries in @err — do not silently correct them.

Then resume from @state.next_act as normal.
```

---

## Load with shared mounted file

For projects that use `@mount` to reference shared team state. Handles locking and conflict detection.

```
Load the AXL specification from {path/to/axl.spec}.
Then load {path/to/project.axl}, including all @import and @mount declarations.

For any mounted file:
- Check whether @lock exists before writing. If locked by another agent, enter
  read-only mode and report the lock to me.
- If you need to write to a mounted file, acquire @lock first, write, then release it.
- If a conflict is detected (mounted file changed since last read), write a CONFLICT
  entry to @err and do not overwrite — report the conflict to me instead.

Then resume from @state.next_act as normal.
```

---

## Compact session (patch mode)

For large project files where only a few fields change per session. Instructs the agent to prefer writing `.axlp` patch files over full rewrites.

```
Load the AXL specification from {path/to/axl.spec}.
Then load {path/to/project.axl}.

For this session: prefer writing a patch file ({path/to/session.axlp}) over
rewriting the full project file. Use @diff operations for all state and plan
updates. Only rewrite the full file if structural changes are required
(new blocks, reordered sections, or more than 10 field changes).

Resume from @state.next_act and proceed.
```

---

## System prompt embed (for harnesses)

A condensed version suitable for inclusion in an agent's system prompt or harness configuration, where brevity matters more than explanation.

```
You are working within an AXL-managed project.
AXL spec: {path/to/axl.spec} — load and internalize before proceeding.
Project file: {path/to/project.axl} — parse all blocks on session start.

Rules:
- Resume from @state.next_act or highest-priority WIP @plan task.
- After each action: update @state, @plan statuses, append to @log (ACT/ERR/NOTE/WARN prefix).
- Write the file (or a .axlp patch) before ending the session.
- Never expand AXL content to prose. Never delete log entries or task lines.
- Never store secret values inline; use *ENV_VAR_NAME references only.
```

---

## Prompt construction tips

**Be explicit about the spec path.** Agents will not locate `axl.spec` automatically. Always include the full or relative path.

**Separate spec loading from task instructions.** Load → parse → then act. Mixing them in one sentence reduces reliability.

**For long-running harnesses,** include the system prompt embed in the base system prompt and pass the project file path as a variable. This avoids repeating the boilerplate on every turn.

**For multi-agent pipelines,** use the handoff prompt when switching agents mid-project. Each agent should add itself to `@meta.agents` on first write — this is part of the spec's agent protocol and should not need reminding, but including it in the handoff prompt adds a useful safeguard.

**Validation pass (optional).** After any session that made significant changes, run the read-only review prompt to confirm the file state looks correct before committing or handing off.
