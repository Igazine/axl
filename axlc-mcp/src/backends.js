/**
 * axlc-mcp — LLM backend abstraction
 *
 * Supports four provider types:
 *   ollama      — Ollama local server (default: http://localhost:11434)
 *   openai      — OpenAI API or any OpenAI-compatible server
 *                 (LM Studio, vLLM, llama.cpp server, LocalAI, Groq, etc.)
 *   anthropic   — Anthropic Messages API
 *   custom      — Arbitrary POST endpoint; user supplies full request template
 *
 * All backends receive the same inputs:
 *   systemPrompt  — AXL spec + compression instructions
 *   userMessage   — the raw human prompt to compress
 *
 * All backends return:
 *   { text: string }  — the model's response text
 */

// ─── Ollama ──────────────────────────────────────────────────────────────────

export async function callOllama(config, systemPrompt, userMessage) {
  const url = (config.baseUrl || 'http://localhost:11434').replace(/\/$/, '');
  const model = config.model || 'qwen2.5:3b';

  const body = {
    model,
    stream: false,
    options: {
      temperature: config.temperature ?? 0.1,
      num_predict: config.maxTokens ?? 512,
    },
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user',   content: userMessage  },
    ],
  };

  const res = await fetch(`${url}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout((config.timeoutMs ?? 30_000)),
  });

  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`Ollama error ${res.status}: ${err}`);
  }

  const data = await res.json();
  const text = data?.message?.content ?? data?.response;
  if (!text) throw new Error('Ollama returned empty response');
  return { text: text.trim() };
}

// ─── OpenAI-compatible (OpenAI, LM Studio, vLLM, llama.cpp, Groq, etc.) ─────

export async function callOpenAICompat(config, systemPrompt, userMessage) {
  const url = (config.baseUrl || 'https://api.openai.com').replace(/\/$/, '');
  const model = config.model || 'gpt-4o-mini';

  const headers = { 'Content-Type': 'application/json' };
  if (config.apiKey) headers['Authorization'] = `Bearer ${config.apiKey}`;

  const body = {
    model,
    temperature: config.temperature ?? 0.1,
    max_tokens: config.maxTokens ?? 512,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user',   content: userMessage  },
    ],
  };

  const res = await fetch(`${url}/v1/chat/completions`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(config.timeoutMs ?? 30_000),
  });

  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`OpenAI-compat error ${res.status}: ${err}`);
  }

  const data = await res.json();
  const text = data?.choices?.[0]?.message?.content;
  if (!text) throw new Error('OpenAI-compat returned empty response');
  return { text: text.trim() };
}

// ─── Anthropic Messages API ───────────────────────────────────────────────────

export async function callAnthropic(config, systemPrompt, userMessage) {
  const url = (config.baseUrl || 'https://api.anthropic.com').replace(/\/$/, '');
  const model = config.model || 'claude-haiku-4-5-20251001';
  const apiKey = config.apiKey || process.env.ANTHROPIC_API_KEY;

  if (!apiKey) throw new Error('Anthropic backend requires apiKey in config or ANTHROPIC_API_KEY env var');

  const body = {
    model,
    max_tokens: config.maxTokens ?? 512,
    system: systemPrompt,
    messages: [
      { role: 'user', content: userMessage },
    ],
  };

  const res = await fetch(`${url}/v1/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(config.timeoutMs ?? 30_000),
  });

  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`Anthropic error ${res.status}: ${err}`);
  }

  const data = await res.json();
  const text = data?.content?.[0]?.text;
  if (!text) throw new Error('Anthropic returned empty response');
  return { text: text.trim() };
}

// ─── Custom endpoint ──────────────────────────────────────────────────────────
// For anything non-standard. User supplies a requestTemplate with
// {{SYSTEM}} and {{USER}} placeholders, and a responsePath to extract
// the text (dot-notation, e.g. "result.text" or "choices.0.message.content").

export async function callCustom(config, systemPrompt, userMessage) {
  if (!config.url) throw new Error('Custom backend requires config.url');

  const templateStr = JSON.stringify(config.requestTemplate || {
    prompt: '{{SYSTEM}}\n\n{{USER}}',
  });

  const bodyStr = templateStr
    .replace(/{{SYSTEM}}/g, systemPrompt.replace(/\\/g, '\\\\').replace(/"/g, '\\"'))
    .replace(/{{USER}}/g,   userMessage.replace(/\\/g, '\\\\').replace(/"/g, '\\"'));

  const headers = { 'Content-Type': 'application/json', ...(config.headers || {}) };

  const res = await fetch(config.url, {
    method: 'POST',
    headers,
    body: bodyStr,
    signal: AbortSignal.timeout(config.timeoutMs ?? 30_000),
  });

  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`Custom backend error ${res.status}: ${err}`);
  }

  const data = await res.json();

  // Walk dot-notation path
  const path = (config.responsePath || 'text').split('.');
  let val = data;
  for (const key of path) {
    val = val?.[key];
    if (val === undefined) break;
  }

  if (typeof val !== 'string' || !val) {
    throw new Error(`Custom backend: could not extract text from response at path "${config.responsePath}". Got: ${JSON.stringify(data).slice(0, 200)}`);
  }

  return { text: val.trim() };
}

// ─── Router ───────────────────────────────────────────────────────────────────

export async function callBackend(config, systemPrompt, userMessage) {
  const provider = (config.provider || 'ollama').toLowerCase();

  switch (provider) {
    case 'ollama':    return callOllama(config, systemPrompt, userMessage);
    case 'openai':
    case 'lmstudio':
    case 'openai-compat': return callOpenAICompat(config, systemPrompt, userMessage);
    case 'anthropic': return callAnthropic(config, systemPrompt, userMessage);
    case 'custom':    return callCustom(config, systemPrompt, userMessage);
    default:
      throw new Error(`Unknown provider "${provider}". Valid: ollama | openai | lmstudio | anthropic | custom`);
  }
}
