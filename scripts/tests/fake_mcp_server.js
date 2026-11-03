// Minimal fake MCP server for testing secret_proxy.js. It never prints a secret on purpose,
// except in the 'echo' and 'image' tools, which exist to prove the proxy scrubs them.
'use strict';
const readline = require('readline');
let calls = 0;
const expect = process.env.FAKE_EXPECT || '';
const send = (id, result) => process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id, result })}\n`);
const text = (id, value) => send(id, { content: [{ type: 'text', text: value }] });

readline.createInterface({ input: process.stdin }).on('line', (line) => {
  const msg = JSON.parse(line);
  if (msg.method === 'initialize') return send(msg.id, { protocolVersion: '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'fake', version: '0' } });
  if (msg.method === 'tools/list') return send(msg.id, { tools: [] });
  if (msg.method !== 'tools/call') return undefined;
  const { name, arguments: args = {} } = msg.params;
  if (name === 'count') return text(msg.id, String(calls));
  calls += 1;
  if (name === 'browser_type') return text(msg.id, JSON.stringify({ matches: args.text === expect, length: args.text.length }));
  if (name === 'browser_fill_form') return text(msg.id, JSON.stringify({ matches: args.fields.every((f) => f.value === expect) }));
  if (name === 'echo') return text(msg.id, `you sent: ${args.text}`);
  if (name === 'image') return send(msg.id, { content: [{ type: 'image', data: expect, mimeType: 'image/png' }] });
  return text(msg.id, `ok ${name} ${JSON.stringify(args)}`);
});
