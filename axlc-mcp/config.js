/**
 * axlc-mcp — configuration
 *
 * Config resolution order (later overrides earlier):
 *   1. Built-in defaults
 *   2. axlc.config.json in cwd (or path from AXLC_CONFIG env var)
 *   3. Environment variables (AXLC_* prefix)
 *
 * See axlc.config.example.json for all options.
 */

import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const DEFAULTS = {
  // LLM backend
  provider:    'ollama',          // ollama | openai | lmstudio | anthropic | custom
  baseUrl:     'http://localhost:11434',
  model:       'qwen2.5:3b',
  apiKey:      null,
  temperature: 0.1,
  maxTokens:   512,
  timeoutMs:   30_000,

  // AXL
  specPath:    './axl.spec',

  // Server
  transport:   'stdio',           // stdio (for MCP) | http (for testing)
  httpPort:    3333,
};

function readConfigFile() {
  const configPath = process.env.AXLC_CONFIG
    ? resolve(process.env.AXLC_CONFIG)
    : resolve(process.cwd(), 'axlc.config.json');

  if (!existsSync(configPath)) return {};

  try {
    return JSON.parse(readFileSync(configPath, 'utf8'));
  } catch (e) {
    throw new Error(`Failed to parse config file at ${configPath}: ${e.message}`);
  }
}

function readEnvOverrides() {
  const overrides = {};
  const map = {
    AXLC_PROVIDER:    'provider',
    AXLC_BASE_URL:    'baseUrl',
    AXLC_MODEL:       'model',
    AXLC_API_KEY:     'apiKey',
    AXLC_TEMPERATURE: 'temperature',
    AXLC_MAX_TOKENS:  'maxTokens',
    AXLC_TIMEOUT_MS:  'timeoutMs',
    AXLC_SPEC_PATH:   'specPath',
    AXLC_TRANSPORT:   'transport',
    AXLC_HTTP_PORT:   'httpPort',
    // Provider-specific shortcuts
    ANTHROPIC_API_KEY: 'apiKey',   // honour standard Anthropic env var
    OPENAI_API_KEY:    'apiKey',
  };

  for (const [env, key] of Object.entries(map)) {
    if (process.env[env] !== undefined) {
      const raw = process.env[env];
      // Coerce numeric fields
      if (['temperature', 'maxTokens', 'timeoutMs', 'httpPort'].includes(key)) {
        overrides[key] = Number(raw);
      } else {
        overrides[key] = raw;
      }
    }
  }

  return overrides;
}

export function loadConfig() {
  const file = readConfigFile();
  const env  = readEnvOverrides();
  return { ...DEFAULTS, ...file, ...env };
}
