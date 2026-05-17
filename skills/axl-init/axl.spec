# AXL — Agent eXchange Language v0.3
# Single specification file. Load once. All .axl files become readable/writable.
# Token-efficient, machine-primary, text-based, cross-agent state and instruction format.
# Not a Markdown replacement. Optimized for inter-agent memory and project continuity.

##──────────────────────────────────────────────────────
## 0. COMMON MISTAKES — read this first
##──────────────────────────────────────────────────────
# These are the most frequent errors made by models reading this spec.
# Each one has caused incorrect output in real sessions. Memorize them.

# MISTAKE 1 — Writing !NOW to disk
#   WRONG:   modified: !NOW
#   CORRECT: modified: @20250510T1435
#   !NOW is a shorthand for use in prompts and spec examples ONLY.
#   It is NEVER valid in a .axl file written to disk.
#   Every model writing an .axl file MUST replace ALL !NOW tokens
#   with the actual current datetime before saving. No exceptions.

# MISTAKE 2 — Deleting or reordering @plan tasks
#   WRONG:   removing a DONE task to "clean up" the plan
#   CORRECT: tasks are never deleted; set status SKIP with a note if needed
#   @plan is an append-only record. Reordering is also forbidden.
#   Agents update STATUS in-place only.

# MISTAKE 3 — Deleting @log entries
#   WRONG:   truncating @log to save space
#   CORRECT: use @logref to point to an external archive file
#   @log is append-only. If it grows too large, rotate via @logref.
#   Never delete entries inline.

# MISTAKE 4 — Mutating @ctx source lines
#   WRONG:   changing "! check docs on session start" to "!! check docs on session start"
#   CORRECT: append the executed directive to @done-ctx verbatim; leave @ctx unchanged
#   @ctx is a permanent declaration. @done-ctx is the execution record.

# MISTAKE 5 — Storing secret values inline
#   WRONG:   db_url: :postgres://user:password@host/db
#   CORRECT: db_url: *DATABASE_URL
#   Secret values are NEVER stored in .axl files.
#   Use *ENV_VAR_NAME to reference the name of the variable only.

# MISTAKE 6 — Inventing tasks or content during markdown conversion
#   WRONG:   adding tasks that seemed implied but weren't written in the source
#   CORRECT: only extract content explicitly present in the source files
#   If uncertain, add a # comment flagging the ambiguity. Never fill gaps silently.

# MISTAKE 7 — Wrapping output in markdown fences
#   WRONG:   ```axl\n@meta\n...```
#   CORRECT: @meta\n...
#   AXL files are plain text. Never wrap in markdown code fences.
#   This applies to all tool output and file writes.

# MISTAKE 8 — Writing version in semver format
#   WRONG:   v: 0.3.0  or  v: 0.2.1
#   CORRECT: v: 0.3
#   AXL versions are MAJOR.MINOR only. Never add a patch segment.

# MISTAKE 9 — Preserving an outdated version field from the project file
#   WRONG:   leaving v: 0.2 unchanged because the project file already had it
#   CORRECT: always update @meta.v to match the loaded spec version (currently 0.3)
#            on first write. The spec version wins over the file version.
#            This is the one field that is always silently upgraded in-place.

##──────────────────────────────────────────────────────
## 1. SYNTAX FUNDAMENTALS
##──────────────────────────────────────────────────────

# STRUCTURE
- File extension: .axl (full file) | .axlp (patch/diff file) | .axlt (type library)
- Encoding: UTF-8, Unix line endings (\n), max line length 512 chars
- Blank lines: ignored everywhere
- Comments: lines where first non-space char is # — stripped on parse, preserved on write
- Blocks: @BLOCKNAME [id] — starts block; ends at next @BLOCK or EOF
- Block names: uppercase; unknown blocks MUST be preserved, not discarded
- Sub-sections inside blocks: >>SECTIONNAME (no spaces)
- Keys: lowercase, [a-z0-9_], max 48 chars
- Values: everything after ": " on same line (trim trailing whitespace)
- Lists: pipe-separated inline  →  key: a|b|c
- Continuation lines: indent with exactly 2 spaces; parser joins with \n
- Dot-keys (vars.KEY) deprecated in v0.2; use >>SECTION grouping instead

# VALUE TYPES (sigil-prefixed — eliminates redundant type annotations)
  plain text   →  key: some text          (default; no sigil)
  url          →  key: :https://example.com
  number       →  key: #42 or #3.14
  boolean      →  key: ?1 or ?0
  date         →  key: @20250510 or @20250510T1435
  id-ref       →  key: $other-task-id
  list         →  key: a|b|c              (sigils apply per element: :url1|:url2)
  empty/null   →  key: ~
  computed now →  key: !NOW               (MUST be replaced with @YYYYMMDDTHHMM before writing to disk)
                                          (!NOW is a draft-time shorthand only — it is NEVER valid
                                          in a file on disk. Any model writing an .axl file is
                                          responsible for resolving ALL !NOW tokens to the actual
                                          current datetime before the file is saved.)
  secret-ref   →  key: *ENV_VAR_NAME      (name only; never store actual secrets)

# ESCAPING (required when literal chars would be misread)
  \|   →  literal pipe in a value (not a list separator)
  \:   →  literal colon at start of value (not a url/sigil)
  \\   →  literal backslash
  \n   →  explicit newline inside a single-line value
  \~   →  literal tilde (not null)
  \!   →  literal exclamation (not a computed token)
  \$   →  literal dollar sign (not a ref)
  Rule: escape only when ambiguous. Plain text values need no escaping.

# IDS AND REFERENCES
  IDs: [a-z0-9-], max 32 chars, unique within their block
  Global ref: $file-alias::block::item-id  (cross-file; file-alias from @import/@mount)
  Local ref:  $item-id                     (same file; resolved in @plan first, then @state)
  Milestone IDs must start with M_

# STATUS TOKENS
  TODO  WAIT  WIP  DONE  SKIP  FAIL  BLOCK  REVIEW  HOLD
  Agents must not invent new status tokens; use HOLD for ambiguous states.

# PRIORITY TOKENS
  P0 (critical/blocking)  P1 (high)  P2 (normal)  P3 (low/nice-to-have)

# FIELD CONSTRAINT MARKERS (used in @type and @meta declarations)
  req   — required; agent must error if missing or ~ on write
  opt   — optional; may be ~
  ro    — read-only after first write
  ro!   — immutable; set once at file creation, never changed

##──────────────────────────────────────────────────────
## 2. CORE BLOCKS
##──────────────────────────────────────────────────────

### @meta  [req, exactly one per file]
Project identity. Agent updates modified, agents, and >>sessions on every write.
  id:        ro! slug — unique project identifier
  v:         ro  AXL spec version (currently 0.3) — format is MAJOR.MINOR only,
             never MAJOR.MINOR.PATCH. Valid examples: 0.3  1.0  Not valid: 0.3.0  0.2.1
  name:      opt human-readable project name (may be ~)
  created:   ro! @date
  modified:  req @date — agent sets current datetime on every write
  agents:    req pipe-list of agent IDs that have written this file
  tags:      opt pipe-list of topic tags
  parent:    opt $global-ref to parent project file (for sub-projects)
  crc:       opt #uint32 — CRC32 of file content excluding this line
             Agent recomputes on write. Reader may skip validation but must not corrupt.

  >>sessions  (opt — agent session tracking for audit and concurrency)
  agent-id: session-id   (one entry per agent; plain string; no sigil required)

  Rules:
  - Each agent writes or updates its own entry on first write of a session
  - If the agent has no session ID, omit the entry entirely — never write ~ or unknown
  - Session IDs are informational only; they are not credentials or secrets
  - Entries persist across sessions; a new session overwrites the previous entry for that agent
  - Agents must not modify other agents' session entries

### @state  [req, one per file]
Current session memory. Agent maintains and updates freely.
  status:    req STATUS token — top-level project health
  focus:     req what this session is/was working on (one line)
  phase:     opt current project phase (free slug)
  blockers:  opt pipe-list of blocker descriptions or $refs (~ if none)
  last_act:  opt last completed action (one line; use ACT: prefix)
  next_act:  opt recommended immediate next action (one line)
  err:       opt last error or anomaly observed (~ if clean)

  >>mem     (agent scratchpad — arbitrary typed key:value pairs)
  KEY: VALUE   (sigils encouraged; one per line; no nesting)

### @plan  [opt, one per file]
Task list. One task per line.

  Line format (colon-delimited):
    id:STATUS:PRIORITY:title[:notes]

  Notes field is optional. Use $ref for cross-task dependencies in notes.
  Milestone: M_id:STATUS:~:title  (no priority field)

  Section grouping:  >>SECTIONNAME  (plain line, no colon format)

  Rules:
  - Agents update STATUS in-place; never reorder or delete lines
  - New tasks appended at end of file or at end of relevant section
  - To remove: set status SKIP with reason in notes field
  - BLOCK tasks must have non-~ notes naming the blocker
  - Dependency in notes: "depends on $other-id" or "blocked by $id"

### @ctx  [opt]
Agent behavioral rules scoped to this project.

  Prefix semantics:
    >   DIRECTIVE           always follow; override agent defaults
    ?   CONDITION => ACTION conditional; agent evaluates before acting
    !   DIRECTIVE           one-time; agent appends to @done-ctx on execution (do NOT mutate @ctx)
    -   NOTE                informational; agent reads, does not act

  Sub-sections via >>SECTIONNAME.
  Directives without a section apply globally within this file.

  Built-in condition tokens (for ? and @hook lines):
    task:done  task:blocked  task:added  task:skipped
    state:changed  session:start  session:end
    file:written  import:missing  err:raised  lock:conflict

### @log  [req, append-only]
Structured event log. Append only; never edit or delete existing lines.

  Format:  @YYYYMMDDTHHMM:AGENT_ID:PREFIX:entry text

  PREFIX tokens (required):
    ACT    action taken
    ERR    error encountered
    NOTE   observation or decision rationale
    WARN   non-fatal anomaly

### @done-ctx  [opt, append-only]
Audit log for executed one-time @ctx directives. Append only; never edit or delete.
Keeps @ctx immutable — one-time directives are never modified in-place.

  Format:  @YYYYMMDDTHHMM:AGENT_ID:directive text (verbatim copy from @ctx)

  Rules:
  - When an agent executes a ! directive from @ctx, it appends the directive
    verbatim to @done-ctx with timestamp and agent ID
  - @ctx source line is NEVER modified (no !! mutation)
  - Before executing any ! directive, agent checks @done-ctx for a matching
    directive text; if found, skips execution (idempotent)
  - If the same ! directive appears in @ctx multiple times, each is tracked
    independently by its full text; duplicates are executed once each

  Example:
    @done-ctx
    @20250510T0900:claude-sonnet-4:check $shared::ref>>urls for latest API docs

### @prompt  [opt, repeatable]
Compressed representation of a human instruction, produced by axlc-mcp before
the prompt reaches the main model. Agents read @prompt blocks as task input.

  id:           ro! slug — unique within file
  created:      ro! !NOW — set by compiler on creation
  op:           req op token — intent classification
  priority:     opt P0–P3 (default P1)
  keywords:     opt pipe-list of key concepts (max 6)
  target:       opt specific module, function, class, or route
  scope:        opt filename or module scope
  tests:        opt ?1 — tests must pass
  commit:       opt ?1 — agent should commit result
  commit_style: opt conventional | freeform
  breaking:     opt ?0 — must not introduce breaking changes
  type_safe:    opt ?1 — strict types required
  review_first: opt ?1 — show diff/plan before applying
  >>raw         verbatim original prompt (word-wrapped at 80 chars)

  Op tokens: add|fix|refactor|update|remove|test|docs|review|deploy|explain|optimize|scaffold|task

  Agents consume @prompt blocks in priority order, highest first.
  After acting on a @prompt block: move it to @done-ctx equivalent by
  appending a log entry and setting a status (or deleting if project policy
  allows; see log_max rotation rules).

### @ref  [opt]
External reference data, grouped by >>SECTIONNAME.
  >>urls   — :url sigil values
  >>paths  — plain relative filesystem paths
  >>envs   — *ENV_VAR_NAME references (names only; never values)
  >>gloss  — TERM: one-line definition

##──────────────────────────────────────────────────────
## 3. MODULARITY BLOCKS
##──────────────────────────────────────────────────────
# Process @import and @mount before all other blocks.

### @import  [opt]
Read-only file references. Agent reads imported content but must not write to those files.

  Format:
    alias: path/to/file.axl[::block][::item-id]
    alias: :https://remote.host/file.axl   (remote; agent fetches if capable)

  Scoping:
    alias          →  entire file's blocks
    alias::plan    →  only the @plan block
    alias::plan::task-id  →  one task line

  Access in this file:  $alias::plan::task-id

  Error handling:
    Missing file   →  ERR: in @log, set @state.err; continue without imported data
    Circular ref   →  detected by alias chain; agent halts and raises err:raised
    Version gap    →  WARN: in @log; best-effort parse; preserve unknown fields

### @mount  [opt]
Read-write shared file references. Both this file and mounted files may be updated
by any agent. Treat as shared mutable state.

  Format:
    alias: path/to/shared.axl[::block]

  Rules:
  - Check @lock before writing to any mounted file
  - On conflict (mounted file changed since last read): write to @err, set @state.err,
    do NOT overwrite — await user resolution
  - On write: add this agent to mounted file's @meta.agents

### @export  [opt]
Named symbols exposed to files that @import this one.
Access pattern for importers: $their-alias::export::NAME

  Format:
    NAME: value-or-$local-ref
    NAME: $plan::task-id        (expose a task's current status)
    NAME: $state>>mem>>KEY      (expose a memory value)

##──────────────────────────────────────────────────────
## 4. EXTENSION BLOCKS
##──────────────────────────────────────────────────────

### @hook  [opt]
Event-triggered directives. Evaluated by agent after each meaningful action.
Fires after @ctx directives, in order of appearance.

  Format:  EVENT => DIRECTIVE_TEXT
  EVENT is any built-in condition token (see @ctx).

  Example:
    task:done    => > update @state.next_act to next TODO by priority
    session:end  => > append NOTE: session summary to @log
    err:raised   => > set @state.status BLOCK and halt

### @type  [opt — may live in a separate .axlt file and be @imported]
Custom field schemas for @state>>mem validation or @plan notes validation.
Agents validate matching fields if @type is present; skip validation if absent.

  Format:
    TYPE_NAME
    >>fields
    FIELD: base-type [constraint]

  Base types:  str  int  bool  date  slug  list  ref  url
  Constraints: min:N  max:N  enum:a|b|c  nonempty

### @logref  [opt]
Reference to an external log file. When present, @log in this file acts as a
rolling window only; full history lives in the referenced file.

  file:     path to the external .axl log file (rotated by month or size)
  log_max:  #integer — max entries to keep in @log before rotation (default #50)
  strategy: month (rotate monthly) | size (rotate at log_max) | never (no rotation)

  Rotation behavior:
  - When @log entry count reaches log_max, agent moves all but the last 10
    entries to the external log file (appending), keeping a short tail in @log
  - External log file uses identical @log format; @meta.id matches parent file
  - If external log file does not exist, agent creates it on first rotation

  Example:
    @logref
    file: ./logs/ecom-api-2025.axl
    log_max: #50
    strategy: size


Sparse update. Apply to a target without rewriting the full file.
Use .axlp extension for patch files.

  Header fields:
    target: path/to/file.axl
    base_modified: @YYYYMMDDTHHMM   (must match target's modified; else apply fails)

  Operations (one per line):
    SET     block::key: new-value
    APPEND  log: @NOW:AGENT_ID:PREFIX:entry text
    STATUS  plan::task-id: NEW_STATUS
    NOTE    plan::task-id: new notes text
    ADD     plan: id:STATUS:P1:new task title
    DEL     plan::task-id:           (sets SKIP with note; never hard-deletes)

  On base_modified mismatch: write conflict to @err, do not apply patch.

### @fence id lang  [opt, repeatable — close with @fence/id]
Raw verbatim content block. Parser does not interpret content between open/close.
Used for code snippets, system prompts, templates, config fragments.

  lang hint (informational): txt  md  ts  py  json  sql  sh  ~
  Agents read @fence blocks; do not modify content unless explicitly instructed.

  Example:
    @fence sys-prompt txt
    You are a senior backend engineer. Reply concisely.
    Use TypeScript strict. Never use any.
    @fence/sys-prompt

### @lock  [opt, ephemeral — written and removed by agent]
Concurrency guard for mounted/shared files.
Agent writes @lock before modifying a shared file; removes it after write.
If @lock exists and locked_by != this agent: enter read-only mode; append intent to @err.

  Fields:
    locked_by: agent-id
    locked_at: !NOW
    ttl:       #seconds (default #120; agent clears after write completes)
    intent:    short description of planned write operation

### @err  [opt, append-only — separate from @log for easy filtering]
Structured error and conflict log.
Format: @NOW:TYPE:AGENT_ID:description

TYPE tokens: PARSE  MISSING  CONFLICT  LOCK  CIRCULAR  VERSION  CONSTRAINT  UNKNOWN

##──────────────────────────────────────────────────────
## 5. COMPACTNESS REFERENCE
##──────────────────────────────────────────────────────

# PLAN FORMAT COMPARISON
  v0.1:  auth-flow  | WIP  | P0 | Implement OAuth2 | blocked on $api-keys
  v0.2:  auth-flow:WIP:P0:Implement OAuth2:blocked on $api-keys
  Savings: ~28% characters; ~25% tokens on typical task lists

# MEM FORMAT COMPARISON
  v0.1:  vars.db_url: postgres://localhost/db
         vars.port: 3000
  v0.2:  >>mem
         db_url: :postgres://localhost/db
         port: #3000
  Savings: prefix "vars." eliminated; sigils clarify type without extra fields

# LOG FORMAT COMPARISON
  v0.1:  20250510T1435 | claude-sonnet-4 | deployed to staging
  v0.2:  @20250510T1435:claude-sonnet-4:ACT:deployed to staging
  Savings: sigil on date; colon delimiters; structured prefix

# MICRO PLAN (5 or fewer tasks, no notes — embed in @state>>mem)
  >>mem
  plan: setup:DONE:P1|auth:WIP:P0|deploy:TODO:P2
  Use only when @plan block would be overkill (scripts, one-shot tasks).

# OMISSION RULES
  - @ref:       omit if no external references
  - @log:       may start empty; first entry on first agent write
  - @meta.name: may be ~ if id is self-explanatory
  - @meta>>sessions: omit entirely if no agent has a session ID to record
  - All opt fields: may be omitted entirely (not just set to ~)
  - @ctx, @hook, @type, @diff, @fence, @lock, @err, @done-ctx: all optional; omit freely

##──────────────────────────────────────────────────────
## 6. VERSIONING AND MIGRATION
##──────────────────────────────────────────────────────

# CURRENT VERSION: 0.3
# Agents parsing v0.2 files should:
  - Treat absence of @meta>>sessions as equivalent to an empty >>sessions section
  - Write back in v0.3 format ONLY if user explicitly requests migration
  - Otherwise preserve original format on rewrite (no silent upgrades)

# Agents parsing v0.1 files should:
  - Accept pipe-delimited plan (|) as equivalent to colon-delimited (:)
  - Accept vars.KEY as equivalent to >>mem KEY
  - Accept pipe-delimited log as equivalent to colon-delimited log

# UNKNOWN BLOCK RULE
  Agents MUST preserve unknown @BLOCKNAME blocks verbatim on any write.
  Never discard content not recognized by current spec version.
  New fields in known blocks from newer spec versions: preserve write-through.

##──────────────────────────────────────────────────────
## 7. AGENT PROTOCOL (meta-instructions for this spec)
##──────────────────────────────────────────────────────

On receiving instruction to load this spec:
  1. Confirm understanding of AXL v0.3 format.
  2. Process @import and @mount first; resolve aliases before any other block.
  3. Check @lock on any mounted file before writing.
  4. Load @type definitions (local or imported .axlt) for validation context.
  5. Parse all blocks; preserve unknown blocks verbatim.
  6. Resume work: @state.focus → @state.next_act → highest-priority WIP @plan task.
  7. Register @ctx directives and @hook triggers.
  8. Load @done-ctx; build a set of already-executed ! directive texts for deduplication.

On each meaningful action:
  a. Update @state fields (focus, last_act, next_act, err)
  b. Update @plan task STATUS in-place (never reorder)
  c. Append structured entry to @log (ACT/ERR/NOTE/WARN prefix)
  d. Resolve ALL !NOW tokens to the actual current datetime (@YYYYMMDDTHHMM)
     before writing — including @meta.modified and any other field containing !NOW.
     !NOW MUST NOT appear in any file written to disk. It is a shorthand for
     use in prompts and spec examples only.
  e. If @meta.v does not match the loaded spec version (currently 0.3), update
     it silently on first write. This is the one field agents always upgrade
     in-place without requiring explicit user instruction.
  e. Write or update own entry in @meta>>sessions if a session ID is available.
     Only write your own entry. Never modify another agent's session entry.
  f. Recompute @meta.crc if field is present
  g. Evaluate and fire applicable @hook events
  h. For any ! directive being executed: check @done-ctx first; if not present,
     execute and append to @done-ctx; if already present, skip silently

On session end:
  - Fire session:end hooks
  - Write final @state and @log
  - Release @lock if held
  - Prefer .axlp patch files for large files with small changes

Absolute rules:
  - NEVER write !NOW to disk — always resolve to @YYYYMMDDTHHMM before saving
  - NEVER expand AXL content to Markdown prose unless explicitly asked
  - NEVER reorder blocks or remove comments
  - NEVER store secret values inline; use *ENV_VAR_NAME references only
  - NEVER hard-delete @plan tasks, @log entries, or @done-ctx entries
  - NEVER mutate @ctx source lines (especially ! directives); use @done-ctx instead
  - NEVER modify another agent's @meta>>sessions entry
  - On parse error: write @err entry, set @state.err, continue with valid content

##──────────────────────────────────────────────────────
## 8. COMPLETE EXAMPLE (v0.3)
##──────────────────────────────────────────────────────

  @import
  shared: ./team-shared.axl::ref
  types:  ./project.axlt

  @meta
  id: ecom-api
  v: 0.3
  created: @20250401
  modified: @20250510T1435
  agents: claude-sonnet-4|cursor-agent
  tags: api|typescript|postgres
  >>sessions
  claude-sonnet-4: ses_abc123xyz
  cursor-agent:    cur_ses_789def

  @state
  status: WIP
  focus: stripe webhook HMAC failure in staging
  blockers: $stripe-wh
  last_act: ACT:deployed /orders; all tests pass
  next_act: debug HMAC mismatch; check *STRIPE_WH_SECRET in Railway
  err: ~
  >>mem
  node_ver: #22
  staging_url: :https://ecom-api-staging.up.railway.app
  coverage: #84
  stripe_wh_secret_ref: *STRIPE_WH_SECRET

  @plan
  >>infra
  infra:DONE:P1:Railway + Postgres + env vars
  ci:DONE:P1:GitHub Actions lint/test/deploy
  >>auth
  auth-jwt:DONE:P0:JWT middleware
  auth-refresh:DONE:P0:Refresh token rotation
  >>payments
  stripe-intent:DONE:P0:Create PaymentIntent on order
  stripe-wh:BLOCK:P0:Webhook handler:HMAC sig fails staging — see *STRIPE_WH_SECRET
  stripe-refund:TODO:P0:Refund via API:depends on $orders-cancel
  >>milestones
  M_beta:WIP:~:Beta — payments functional

  @ctx
  >>stack
  > Node 22, TypeScript 5.4 strict, Express 5
  > PostgreSQL 16 via pg; Zod validation; Stripe SDK v16
  >>workflow
  > conventional commits: feat|fix|chore|docs
  > all P0 routes need integration test before DONE
  ? task:done AND task starts with stripe => verify in staging before DONE
  ? task:blocked => add to @state.blockers; set @state.err to blocker summary
  ! session:start => check $shared::ref>>urls for latest API docs
  >>secrets
  - all secrets via *ENV_VAR_NAME only; never inline values

  @hook
  task:done    => > append ACT: entry to @log with task id
  err:raised   => > set @state.status BLOCK
  session:end  => > append NOTE: session summary to @log

  @log
  @20250401T1000:cursor-agent:ACT:project init; Railway + Postgres provisioned
  @20250510T1310:claude-sonnet-4:ACT:deployed /orders to staging; tests pass
  @20250510T1435:claude-sonnet-4:ERR:stripe webhook HMAC mismatch in staging

  @done-ctx
  @20250401T1000:cursor-agent:check $shared::ref>>urls for latest API docs

  @ref
  >>urls
  stripe-wh-docs: :https://stripe.com/docs/webhooks/signatures
  >>paths
  src: ./src
  migrations: ./migrations
  >>envs
  stripe_wh: *STRIPE_WH_SECRET
  db: *DATABASE_URL

## END OF SPEC v0.2
