#!/usr/bin/env node
/**
 * axlc-mcp — MCP server
 *
 * Exposes tools to any MCP-compatible agent or harness:
 *
 *   compress_prompt   — converts a human prompt to an AXL @prompt block
 *   append_prompt     — compress + append the block to a project .axl file
 *   convert_markdown  — converts one or more MD files into a .axl project file
 *   list_backends     — returns current backend config (no API keys)
 *
 * Transport: stdio (default, for Claude Desktop / Cursor / Claude Code)
 *            http   (set transport: "http" in config, for testing / custom harnesses)
 *
 * Start:
 *   node src/index.js
 *   AXLC_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-... node src/index.js
 */

import { McpServer }      from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z }              from 'zod';
import { readFileSync, appendFileSync, existsSync, writeFileSync } from 'fs';
import { resolve, dirname, basename }        from 'path';

import { loadConfig }     from './config.js';
import { loadSpec, buildSystemPrompt } from './prompt.js';
import { buildConversionSystemPrompt } from './convert.js';
import { callBackend }    from './backends.js';

// ─── Boot ─────────────────────────────────────────────────────────────────────

const config = loadConfig();

let spec;
try {
  spec = loadSpec(config.specPath);
} catch (e) {
  process.stderr.write(`[axlc-mcp] Warning: ${e.message}\n`);
  process.stderr.write(`[axlc-mcp] Continuing without spec — compression quality will be reduced.\n`);
  spec = '# AXL spec not found. Compress the prompt into a compact AXL @prompt block.';
}

const systemPrompt = buildSystemPrompt(spec);

process.stderr.write(`[axlc-mcp] Starting — provider: ${config.provider}, model: ${config.model}\n`);

// ─── MCP server ───────────────────────────────────────────────────────────────

const server = new McpServer({
  name:    'axlc-mcp',
  version: '0.1.0',
});

// ── Tool: compress_prompt ────────────────────────────────────────────────────

server.tool(
  'compress_prompt',
  'Convert a human-written prompt into a compact AXL @prompt block using a local or remote LLM. Returns the AXL block as a string.',
  {
    prompt: z.string().min(1).describe('The human-written prompt to compress into AXL format'),
    priority: z.enum(['P0','P1','P2','P3']).optional()
      .describe('Override inferred priority. Default: P1'),
    op: z.string().optional()
      .describe('Override inferred op token (add|fix|refactor|update|remove|test|docs|review|deploy|explain|optimize|scaffold|task)'),
  },
  async ({ prompt, priority, op }) => {
    let userMessage = prompt;

    // Prepend explicit overrides as hints to the model
    const hints = [];
    if (op)       hints.push(`op hint: ${op}`);
    if (priority) hints.push(`priority hint: ${priority}`);
    if (hints.length) {
      userMessage = `[${hints.join(', ')}]\n\n${prompt}`;
    }

    let result;
    try {
      result = await callBackend(config, systemPrompt, userMessage);
    } catch (e) {
      return {
        isError: true,
        content: [{ type: 'text', text: `axlc-mcp backend error: ${e.message}` }],
      };
    }

    const axlBlock = result.text;

    // Basic sanity check — model should have returned an @prompt block
    if (!axlBlock.includes('@prompt')) {
      return {
        isError: true,
        content: [{
          type: 'text',
          text: `axlc-mcp: model did not return a valid @prompt block.\nRaw output:\n${axlBlock}`,
        }],
      };
    }

    return {
      content: [{ type: 'text', text: axlBlock }],
    };
  }
);

// ── Tool: append_prompt ───────────────────────────────────────────────────────

server.tool(
  'append_prompt',
  'Compress a human prompt into an AXL @prompt block and append it to an existing project .axl file.',
  {
    prompt: z.string().min(1).describe('The human-written prompt to compress'),
    projectFile: z.string().min(1).describe('Absolute or relative path to the target .axl file'),
    priority: z.enum(['P0','P1','P2','P3']).optional(),
    op: z.string().optional(),
  },
  async ({ prompt, projectFile, priority, op }) => {
    const filePath = resolve(projectFile);

    if (!existsSync(filePath)) {
      return {
        isError: true,
        content: [{ type: 'text', text: `axlc-mcp: file not found: ${filePath}` }],
      };
    }

    // Reuse compress_prompt logic
    let userMessage = prompt;
    const hints = [];
    if (op)       hints.push(`op hint: ${op}`);
    if (priority) hints.push(`priority hint: ${priority}`);
    if (hints.length) userMessage = `[${hints.join(', ')}]\n\n${prompt}`;

    let result;
    try {
      result = await callBackend(config, systemPrompt, userMessage);
    } catch (e) {
      return {
        isError: true,
        content: [{ type: 'text', text: `axlc-mcp backend error: ${e.message}` }],
      };
    }

    const axlBlock = result.text;

    if (!axlBlock.includes('@prompt')) {
      return {
        isError: true,
        content: [{
          type: 'text',
          text: `axlc-mcp: model did not return a valid @prompt block.\nRaw output:\n${axlBlock}`,
        }],
      };
    }

    try {
      appendFileSync(filePath, '\n' + axlBlock + '\n', 'utf8');
    } catch (e) {
      return {
        isError: true,
        content: [{ type: 'text', text: `axlc-mcp: failed to write to ${filePath}: ${e.message}` }],
      };
    }

    return {
      content: [{
        type: 'text',
        text: `Appended @prompt block to ${filePath}\n\n${axlBlock}`,
      }],
    };
  }
);

// ── Tool: convert_markdown ────────────────────────────────────────────────────

server.tool(
  'convert_markdown',
  'Convert one or more Markdown project files (ROADMAP.md, ARCHITECTURE.md, TODO.md, etc.) into a single AXL project file. Human-initiated migration tool — not a pipeline step. Returns the generated AXL content and optionally writes it to disk.',
  {
    files: z.array(z.string()).min(1).max(10)
      .describe('Absolute or relative paths to the Markdown files to convert. Pass multiple files to merge them into one .axl file.'),
    outFile: z.string().optional()
      .describe('Path to write the generated .axl file. If omitted, returns content only without writing.'),
    projectId: z.string().optional()
      .describe('Override the inferred project id slug. Use if the MD files do not have a clear project name.'),
    model: z.string().optional()
      .describe('Override the configured model for this call only. Conversion benefits from a more capable model than prompt compression.'),
  },
  async ({ files, outFile, projectId, model }) => {

    // ── Read and validate all input files ──────────────────────────────────────
    const fileContents = [];
    for (const f of files) {
      const p = resolve(f);
      if (!existsSync(p)) {
        return {
          isError: true,
          content: [{ type: 'text', text: `axlc-mcp: file not found: ${p}` }],
        };
      }
      const text = readFileSync(p, 'utf8');
      if (!text.trim()) {
        return {
          isError: true,
          content: [{ type: 'text', text: `axlc-mcp: file is empty: ${p}` }],
        };
      }
      fileContents.push({ path: p, name: basename(p), text });
    }

    // ── Build user message ─────────────────────────────────────────────────────
    // Each file is clearly labelled so the model can distinguish sources
    // when merging multiple files or noting conflicts.
    const sections = fileContents.map(f =>
      `## SOURCE FILE: ${f.name}\n\n${f.text}`
    ).join('\n\n---\n\n');

    const projectHint = projectId
      ? `\nProject id override: use "${projectId}" as the @meta.id slug.\n`
      : '';

    const userMessage =
      `Convert the following Markdown file(s) to AXL format.${projectHint}\n\n${sections}`;

    // ── Call backend (allow per-call model override) ────────────────────────────
    // Conversion is more demanding than prompt compression — caller may want
    // to route to a larger model while keeping the default small for compress_prompt.
    const callConfig = model ? { ...config, model } : config;
    const conversionSystemPrompt = buildConversionSystemPrompt(spec);

    let result;
    try {
      result = await callBackend(callConfig, conversionSystemPrompt, userMessage);
    } catch (e) {
      return {
        isError: true,
        content: [{ type: 'text', text: `axlc-mcp backend error: ${e.message}` }],
      };
    }

    const axlContent = result.text;

    // ── Sanity check ───────────────────────────────────────────────────────────
    const requiredBlocks = ['@meta', '@state', '@log'];
    const missing = requiredBlocks.filter(b => !axlContent.includes(b));
    if (missing.length) {
      return {
        isError: true,
        content: [{
          type: 'text',
          text: `axlc-mcp: generated output is missing required blocks: ${missing.join(', ')}\n\nRaw output:\n${axlContent}`,
        }],
      };
    }

    // ── Write to disk if requested ─────────────────────────────────────────────
    if (outFile) {
      const outPath = resolve(outFile);
      try {
        writeFileSync(outPath, axlContent + '\n', 'utf8');
        return {
          content: [{
            type: 'text',
            text: `Converted ${fileContents.length} file(s) → ${outPath}\n\nReview before using — verify task statuses, priorities, and any # comments flagging ambiguous content.\n\n${axlContent}`,
          }],
        };
      } catch (e) {
        return {
          isError: true,
          content: [{ type: 'text', text: `axlc-mcp: failed to write ${outPath}: ${e.message}` }],
        };
      }
    }

    // ── Return without writing ─────────────────────────────────────────────────
    return {
      content: [{
        type: 'text',
        text: `Converted ${fileContents.length} file(s). Review output, then re-run with outFile to save.\n\n${axlContent}`,
      }],
    };
  }
);

// ── Tool: list_backends ───────────────────────────────────────────────────────

server.tool(
  'list_backends',
  'Return the current axlc-mcp backend configuration (provider, model, baseUrl). Does not expose API keys.',
  {},
  async () => {
    return {
      content: [{
        type: 'text',
        text: [
          `provider: ${config.provider}`,
          `model:    ${config.model}`,
          `baseUrl:  ${config.baseUrl}`,
          `specPath: ${config.specPath}`,
          `timeout:  ${config.timeoutMs}ms`,
        ].join('\n'),
      }],
    };
  }
);

// ─── Transport ────────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
process.stderr.write('[axlc-mcp] Ready on stdio\n');
