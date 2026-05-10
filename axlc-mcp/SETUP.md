# axlc-mcp — Setup Guide

`axlc-mcp` is an MCP server that compresses human prompts into compact AXL `@prompt` blocks before they reach your main model. It uses a configurable LLM backend — local (Ollama, LM Studio) or remote (OpenAI, Anthropic, any OpenAI-compatible API).

---

## How it fits in your workflow

```
You type a prompt
       │
       ▼
axlc-mcp  ←── axl.spec (loaded once at startup)
       │
       ▼
small/cheap LLM  (local Ollama, LM Studio, or remote)
       │
       ▼
@prompt AXL block  (compact, typed, token-efficient)
       │
       ▼
your main agent  (Claude, Cursor, Claude Code, etc.)
```

The main agent receives the compressed block instead of the verbose original. It already has `axl.spec` loaded, so it knows exactly what to do with a `@prompt` block.

---

## Prerequisites

- Node.js 22+
- One of:
  - [Ollama](https://ollama.com) (recommended for local use — free, private, fast)
  - LM Studio (GUI-based local model server)
  - An OpenAI, Anthropic, or compatible API key

---

## 1. Install

```bash
git clone https://github.com/Igazine/axl
cd axl/axlc-mcp
npm install
```

---

## 2. Configure the LLM backend

Copy the example config and edit it:

```bash
cp axlc.config.example.json axlc.config.json
```

Then edit `axlc.config.json`. Pick the section that matches your setup:

### Option A — Ollama (local, recommended)

Install Ollama from [ollama.com](https://ollama.com), then pull a model:

```bash
ollama pull qwen2.5:3b        # ~2GB — good balance of speed and quality
# or
ollama pull phi4-mini          # ~2.5GB — strong reasoning, slightly slower
# or
ollama pull llama3.2:3b        # ~2GB — good general purpose
```

`axlc.config.json`:
```json
{
  "provider":    "ollama",
  "baseUrl":     "http://localhost:11434",
  "model":       "qwen2.5:3b",
  "temperature": 0.1,
  "maxTokens":   512,
  "specPath":    "../axl.spec"
}
```

### Option B — LM Studio

Start LM Studio, load a model, and enable the local server (default port 1234).

`axlc.config.json`:
```json
{
  "provider":    "openai",
  "baseUrl":     "http://localhost:1234",
  "model":       "lmstudio-community/Qwen2.5-3B-Instruct-GGUF",
  "apiKey":      "lm-studio",
  "temperature": 0.1,
  "maxTokens":   512,
  "specPath":    "../axl.spec"
}
```

The model name must match what LM Studio reports in its model list.

### Option C — OpenAI

```json
{
  "provider":    "openai",
  "baseUrl":     "https://api.openai.com",
  "model":       "gpt-4o-mini",
  "apiKey":      "sk-...",
  "temperature": 0.1,
  "maxTokens":   512,
  "specPath":    "../axl.spec"
}
```

Or set `OPENAI_API_KEY` in your environment and omit `apiKey` from the file.

### Option D — Anthropic

```json
{
  "provider":    "anthropic",
  "model":       "claude-haiku-4-5-20251001",
  "apiKey":      "sk-ant-...",
  "temperature": 0.1,
  "maxTokens":   512,
  "specPath":    "../axl.spec"
}
```

Or set `ANTHROPIC_API_KEY` in your environment.

### Option E — Any OpenAI-compatible server

Groq, vLLM, llama.cpp server, LocalAI, Together, Fireworks, etc.:

```json
{
  "provider":    "openai",
  "baseUrl":     "https://api.groq.com/openai",
  "model":       "llama-3.1-8b-instant",
  "apiKey":      "gsk_...",
  "temperature": 0.1,
  "maxTokens":   512,
  "specPath":    "../axl.spec"
}
```

### Option F — Custom endpoint

For any server with a non-standard request/response format:

```json
{
  "provider":      "custom",
  "url":           "http://localhost:8080/generate",
  "headers":       { "Authorization": "Bearer mytoken" },
  "requestTemplate": {
    "system": "{{SYSTEM}}",
    "prompt": "{{USER}}",
    "max_tokens": 512
  },
  "responsePath":  "generated_text",
  "specPath":      "../axl.spec"
}
```

`{{SYSTEM}}` and `{{USER}}` are replaced at runtime. `responsePath` is a dot-notation path into the JSON response.

---

## 3. Point specPath to your axl.spec

The `specPath` field tells the server where to find `axl.spec`. It's loaded once at startup and injected into the system prompt. Use a path relative to the `axlc-mcp/` directory, or an absolute path.

```json
"specPath": "../axl.spec"
```

---

## 4. Wire to your agent or harness

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "axlc": {
      "command": "node",
      "args": ["/absolute/path/to/axl/axlc-mcp/index.js"],
      "cwd": "/absolute/path/to/axl/axlc-mcp"
    }
  }
}
```

Restart Claude Desktop. You'll see `axlc` in the MCP tools list.

### Claude Code

```bash
claude mcp add axlc node /absolute/path/to/axl/axlc-mcp/index.js
```

Or add to your project's `.claude/mcp.json`:

```json
{
  "servers": {
    "axlc": {
      "command": "node",
      "args": ["./axlc-mcp/index.js"],
      "cwd": "./axlc-mcp"
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "axlc": {
      "command": "node",
      "args": ["/absolute/path/to/axl/axlc-mcp/index.js"]
    }
  }
}
```

### Any MCP-compatible harness

The server runs on **stdio** transport (the MCP standard). Start it with:

```bash
node /path/to/axlc-mcp/index.js
```

It reads JSON-RPC from stdin, writes to stdout. Stderr is used for log messages.

---

## 5. Available tools

Once connected, your agent has access to three tools:

### `compress_prompt`
Convert a human prompt into an AXL `@prompt` block.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | yes | The human prompt to compress |
| `priority` | P0–P3 | no | Override inferred priority |
| `op` | string | no | Override inferred op token |

### `append_prompt`
Compress a prompt and append the result to an existing `.axl` file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | yes | The human prompt to compress |
| `projectFile` | string | yes | Path to the target `.axl` file |
| `priority` | P0–P3 | no | Override inferred priority |
| `op` | string | no | Override inferred op token |

### `convert_markdown`
Convert one or more Markdown project files into a single AXL project file. Human-initiated migration — not a pipeline step. Always review the output before saving.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `files` | string[] | yes | Paths to the Markdown files to convert (max 10) |
| `outFile` | string | no | Path to write the `.axl` file. If omitted, returns content only |
| `projectId` | string | no | Override the inferred project id slug |
| `model` | string | no | Override the configured model for this call only |

**Which files to pass:**

| File | Converts well |
|------|--------------|
| `ROADMAP.md` | ✅ Tasks, milestones, phases → `@plan` |
| `TODO.md` / `BACKLOG.md` | ✅ Task lists → `@plan` |
| `ARCHITECTURE.md` | ✅ Stack, constraints → `@ctx`; URLs → `@ref` |
| `CONTEXT.md` / `MEMORY.md` | ✅ Agent state files → `@state` |
| `PLAN.md` | ⚠️ Tasks convert; prose reasoning is discarded |
| `README.md` | ⚠️ Only actionable parts extracted; narrative discarded |
| `CHANGELOG.md` | ❌ Leave as Markdown |
| ADRs / design docs | ❌ Leave as Markdown |

**Recommended workflow:**

```
# 1. Dry run — review without writing
Use convert_markdown with files: ["./ROADMAP.md", "./TODO.md"]

# 2. If output looks good, save it
Use convert_markdown with files: ["./ROADMAP.md", "./TODO.md"], outFile: "./project.axl"

# 3. Load the spec and review the generated file
Use the larger model for conversion if the default is weak on structure:
Use convert_markdown with files: ["./ROADMAP.md"], outFile: "./project.axl", model: "qwen2.5:7b"
```

**Note on model choice:** conversion is more demanding than prompt compression — it needs to parse prose intent and produce structured multi-block output. If your default model (e.g. a 3B) produces malformed output, override with a larger one for this tool specifically using the `model` parameter. The compressed `@prompt` workflow can still use the smaller model.

### `list_backends`
Returns the current provider, model, and baseUrl. Does not expose API keys.

---

## 6. Test it

Start the server manually and send a test message:

```bash
cd axlc-mcp
nodeindex.js &

echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"compress_prompt","arguments":{"prompt":"refactor the auth module to use middleware, tests must still pass"}}}' \
  | nodeindex.js
```

Or, if your harness is connected, just ask your agent:

```
Use the compress_prompt tool to compress: "fix the login route, it returns 500 on valid credentials, this is P0"
```

Expected output:
```
@prompt
id: fix-login-500
created: !NOW
op: fix
priority: P0
keywords: login|route|500|credentials
target: login-route
>>raw
  fix the login route, it returns 500 on valid credentials, this is P0
```

---

## 7. Environment variables

All config fields can be overridden via environment variables:

| Variable | Config key |
|----------|------------|
| `AXLC_PROVIDER` | `provider` |
| `AXLC_BASE_URL` | `baseUrl` |
| `AXLC_MODEL` | `model` |
| `AXLC_API_KEY` | `apiKey` |
| `AXLC_TEMPERATURE` | `temperature` |
| `AXLC_MAX_TOKENS` | `maxTokens` |
| `AXLC_TIMEOUT_MS` | `timeoutMs` |
| `AXLC_SPEC_PATH` | `specPath` |
| `ANTHROPIC_API_KEY` | `apiKey` (Anthropic) |
| `OPENAI_API_KEY` | `apiKey` (OpenAI) |
| `AXLC_CONFIG` | path to config file |

Environment variables take precedence over `axlc.config.json`.

---

## 8. Model selection guidance

For prompt compression specifically, you want a model that follows structured output instructions reliably. Bigger is not always better here — a well-prompted 3B model outperforms a poorly-prompted 70B one for this task.

| Model | Size | Notes |
|-------|------|-------|
| `qwen2.5:3b` | 2GB | Best default — strong instruction following, fast |
| `phi4-mini` | 2.5GB | Strong reasoning, good for ambiguous prompts |
| `llama3.2:3b` | 2GB | Good general purpose, slightly less structured |
| `qwen2.5:7b` | 4.7GB | Better on complex multi-constraint prompts |
| `gpt-4o-mini` | API | Fast, reliable, cheap — good remote option |
| `claude-haiku-4-5` | API | Excellent instruction following |

Temperature `0.1` is recommended for all models — you want deterministic structured output, not creativity.

---

## Troubleshooting

**`axl.spec not found`** — Check `specPath` in your config. Path is relative to the `axlc-mcp/` directory.

**`Ollama error 404`** — The model isn't pulled yet. Run `ollama pull <model-name>`.

**`model did not return a valid @prompt block`** — The model ignored the output format instructions. Try a different model, or reduce `temperature` to `0.05`.

**Server not appearing in harness** — Check the absolute path in your harness config. Node must be in PATH. Check harness logs for startup errors.
