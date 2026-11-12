#!/usr/bin/env node
/*
 * secret_proxy.js: lets an MCP server type secrets without the model ever seeing them.
 *
 * It wraps ONE MCP server. Claude Code starts this proxy instead of the server, and the
 * proxy starts the real server as its child process:
 *
 *     Claude  <->  secret_proxy.js  <->  real MCP server
 *
 * Going in (Claude -> server), for tools/call requests only:
 *   - A string containing `secret:NAME` is replaced by the value of NAME from the secrets file,
 *     but only in the tools listed in --allow-tools (the ones that type text).
 *   - A reference in any other tool is blocked: the call never reaches the server and Claude
 *     gets an error. A reference to a secret that is not set is blocked the same way.
 * Going out (server -> Claude), for every message and for the server's stderr:
 *   - Every known secret value is replaced by `***`. Image content is passed through untouched.
 * Everything else is forwarded unchanged.
 * Optionally (--output-filters), the big results of named tools are shrunk before they reach Claude
 * (screenshots become a path plus a small preview, page source becomes a compact element list); see output_filters.js.
 *
 * Usage:
 *   node secret_proxy.js --allow-tools browser_type,browser_fill_form [--secrets-file FILE]
 *        [--output-filters tool:filter,...] [--max-image-px 900] -- <server command> [args...]
 *
 * Secrets file: ~/exploratory-testing/secrets.env (same format check_secret.py reads), re-read
 * whenever it changes. Values are never logged. Error messages name the secret, never its value.
 * Needs only Node 18+; no packages.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn, spawnSync } = require('child_process');
const { StringDecoder } = require('string_decoder');
const { FILTERS, applyFilter } = require('./output_filters');

const REF_RE = /secret:([A-Z_][A-Z0-9_]*)/g;
const NAME_RE = /^[A-Z_][A-Z0-9_]*$/;
const MASK = '***';
// Shorter values cannot be hidden without mangling ordinary output.
const MIN_SCRUB_LENGTH = 4;

// --------------------------------------------------------------------------- arguments

function parseArgs(argv) {
  const sep = argv.indexOf('--');
  if (sep === -1 || sep === argv.length - 1) {
    throw new Error('usage: secret_proxy.js [--allow-tools a,b] [--secrets-file FILE] -- <server command> [args...]');
  }
  const own = argv.slice(0, sep);
  const command = argv.slice(sep + 1);
  const opts = {
    allow: new Set(),
    secretsFile: path.join(os.homedir(), 'exploratory-testing', 'secrets.env'),
    filters: new Map(),
    filterOpts: {},
    command,
  };
  for (let i = 0; i < own.length; i += 1) {
    if (own[i] === '--allow-tools') {
      opts.allow = new Set((own[++i] || '').split(',').map((s) => s.trim()).filter(Boolean));
    } else if (own[i] === '--secrets-file') {
      opts.secretsFile = own[++i];
    } else if (own[i] === '--output-filters') {
      // tool:filter pairs, e.g. appium_screenshot:appium-screenshot,appium_get_page_source:appium-page-source
      for (const pair of (own[++i] || '').split(',').map((s) => s.trim()).filter(Boolean)) {
        const [tool, filter] = pair.split(':');
        if (!tool || !FILTERS[filter]) throw new Error(`unknown output filter in "${pair}"; known: ${Object.keys(FILTERS).join(', ')}`);
        opts.filters.set(tool, filter);
      }
    } else if (own[i] === '--max-image-px') {
      opts.filterOpts.maxImagePx = Number(own[++i]) || 900;
    } else {
      throw new Error(`unknown option ${own[i]}`);
    }
  }
  return opts;
}

// --------------------------------------------------------------------------- secrets

function parseSecrets(text) {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1); // BOM from some Windows editors
  const values = {};
  for (const raw of text.split(/\r\n|\n|\r/)) {
    if (!raw.trim() || raw.trimStart().startsWith('#')) continue;
    const eq = raw.indexOf('=');
    if (eq < 0) continue;
    const name = raw.slice(0, eq).trim();
    if (!NAME_RE.test(name)) continue;
    values[name] = raw.slice(eq + 1); // verbatim; the last duplicate wins, like check_secret.py
  }
  return values;
}

function createSecretStore(file) {
  let cache = { key: null, values: {}, scrub: [] };
  return {
    load() {
      let stat;
      try {
        stat = fs.statSync(file);
      } catch {
        cache = { key: 'missing', values: {}, scrub: [] };
        return cache;
      }
      const key = `${stat.mtimeMs}:${stat.size}`;
      if (cache.key === key) return cache;
      let text;
      try {
        text = fs.readFileSync(file, 'utf8');
      } catch {
        return cache;
      }
      const values = parseSecrets(text);
      const scrub = new Set();
      for (const value of Object.values(values)) {
        if (value.length < MIN_SCRUB_LENGTH) continue;
        scrub.add(value);
        const encoded = encodeURIComponent(value);
        if (encoded !== value) scrub.add(encoded);
      }
      cache = { key, values, scrub: [...scrub].sort((a, b) => b.length - a.length) };
      return cache;
    },
  };
}

// --------------------------------------------------------------------------- JSON walking

function findRefs(node, found = new Set()) {
  if (typeof node === 'string') {
    for (const match of node.matchAll(REF_RE)) found.add(match[1]);
  } else if (Array.isArray(node)) {
    node.forEach((item) => findRefs(item, found));
  } else if (node && typeof node === 'object') {
    Object.values(node).forEach((item) => findRefs(item, found));
  }
  return found;
}

function substituteDeep(node, values) {
  if (typeof node === 'string') return node.replace(REF_RE, (whole, name) => (values[name] ? values[name] : whole));
  if (Array.isArray(node)) return node.map((item) => substituteDeep(item, values));
  if (node && typeof node === 'object') {
    const out = {};
    for (const [key, item] of Object.entries(node)) out[key] = substituteDeep(item, values);
    return out;
  }
  return node;
}

function scrubString(text, list) {
  let out = text;
  for (const value of list) {
    if (out.includes(value)) out = out.split(value).join(MASK);
  }
  return out;
}

function scrubDeep(node, list) {
  if (typeof node === 'string') return scrubString(node, list);
  if (Array.isArray(node)) return node.map((item) => scrubDeep(item, list));
  if (node && typeof node === 'object') {
    if (node.type === 'image') return node; // pixels cannot be scrubbed; do not mangle base64
    const out = {};
    for (const [key, item] of Object.entries(node)) out[key] = scrubDeep(item, list);
    return out;
  }
  return node;
}

// --------------------------------------------------------------------------- line framing

// MCP over stdio is one JSON message per line.
function lineSplitter(onLine) {
  const decoder = new StringDecoder('utf8');
  let buffer = '';
  return {
    push(chunk) {
      buffer += decoder.write(chunk);
      let index;
      while ((index = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, index).replace(/\r$/, '');
        buffer = buffer.slice(index + 1);
        if (line) onLine(line);
      }
    },
    end() {
      buffer += decoder.end();
      const line = buffer.replace(/\r$/, '');
      buffer = '';
      if (line) onLine(line);
    },
  };
}

// --------------------------------------------------------------------------- the proxy

function quoteForWindowsShell(arg) {
  return /^[\w@%+=:,./\\-]+$/.test(arg) ? arg : `"${arg.replace(/"/g, '\\"')}"`;
}

function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(`secret_proxy: ${error.message}\n`);
    process.exit(2);
  }
  const store = createSecretStore(opts.secretsFile);
  const isWindows = process.platform === 'win32';
  const [command, ...args] = opts.command;

  // On Windows, npx is npx.cmd and needs a shell; build one quoted command line.
  const child = isWindows
    ? spawn([command, ...args].map(quoteForWindowsShell).join(' '), { stdio: ['pipe', 'pipe', 'pipe'], shell: true, windowsHide: true })
    : spawn(command, args, { stdio: ['pipe', 'pipe', 'pipe'] });

  child.on('error', (error) => {
    process.stderr.write(`secret_proxy: could not start "${command}": ${error.message}\n`);
    process.exitCode = 1;
    process.stdin.destroy();
  });

  const toServer = (line) => child.stdin.write(`${line}\n`);
  const toClient = (line) => process.stdout.write(`${line}\n`);

  function replyError(id, text) {
    if (id === undefined || id === null) return;
    toClient(JSON.stringify({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text }], isError: true } }));
  }

  // Calls whose result goes through an output filter, by JSON-RPC id.
  const filterByRequest = new Map();

  function fromClient(line) {
    let message;
    try {
      message = JSON.parse(line);
    } catch {
      toServer(line);
      return;
    }
    const call = message && !Array.isArray(message) && message.method === 'tools/call' ? message.params : null;
    if (call && opts.filters.has(call.name) && message.id !== undefined && message.id !== null) {
      filterByRequest.set(String(message.id), opts.filters.get(call.name));
    }
    if (call && call.arguments !== undefined) {
      const names = findRefs(call.arguments);
      if (names.size > 0) {
        if (!opts.allow.has(call.name)) {
          replyError(message.id,
            `Secret references are not allowed in ${call.name}; the call was not sent. ` +
            `Use them only to type into a field with: ${[...opts.allow].join(', ') || '(no tool is enabled)'}.`);
          return;
        }
        const { values } = store.load();
        const missing = [...names].filter((name) => !values[name]);
        if (missing.length > 0) {
          replyError(message.id,
            `Secret not set: ${missing.join(', ')}. The call was not sent. ` +
            'Tell the user to set it in the secrets file. Never ask for the value in chat.');
          return;
        }
        message.params.arguments = substituteDeep(call.arguments, values);
        toServer(JSON.stringify(message));
        return;
      }
    }
    toServer(line);
  }

  function fromServer(line) {
    const { scrub } = store.load();
    let message = null;
    try {
      message = JSON.parse(line);
    } catch {
      message = null;
    }
    if (message && !Array.isArray(message) && message.id !== undefined && message.id !== null && filterByRequest.has(String(message.id))) {
      const filter = filterByRequest.get(String(message.id));
      filterByRequest.delete(String(message.id));
      if (message.result) {
        // Scrub secrets first (in the original text), then shrink; images are never scrubbed.
        const scrubbed = scrub.length > 0 ? scrubDeep(message.result, scrub) : message.result;
        message = { ...message, result: applyFilter(filter, scrubbed, opts.filterOpts) };
        toClient(JSON.stringify(message));
        return;
      }
    }
    if (scrub.length === 0) {
      toClient(line);
      return;
    }
    try {
      toClient(JSON.stringify(scrubDeep(message || JSON.parse(line), scrub)));
    } catch {
      toClient(scrubString(line, scrub));
    }
  }

  const clientLines = lineSplitter(fromClient);
  const serverLines = lineSplitter(fromServer);
  const errorLines = lineSplitter((line) => process.stderr.write(`${scrubString(line, store.load().scrub)}\n`));

  process.stdin.on('data', (chunk) => clientLines.push(chunk));
  process.stdin.on('end', () => {
    clientLines.end();
    child.stdin.end();
    setTimeout(killChild, 2000).unref();
  });
  child.stdout.on('data', (chunk) => serverLines.push(chunk));
  child.stderr.on('data', (chunk) => errorLines.push(chunk));
  child.stdin.on('error', () => {}); // the server may exit before we finish writing

  child.on('close', (code) => {
    serverLines.end();
    errorLines.end();
    if (process.exitCode === undefined) process.exitCode = code === null ? 1 : code;
    process.stdin.destroy();
  });

  function killChild() {
    if (!child.pid || child.exitCode !== null) return;
    if (isWindows) spawnSync('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
    else child.kill('SIGTERM');
  }
  for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
    process.on(signal, () => {
      killChild();
      process.exit(0);
    });
  }
}

if (require.main === module) main();
module.exports = { parseArgs, parseSecrets, findRefs, substituteDeep, scrubDeep, scrubString };
