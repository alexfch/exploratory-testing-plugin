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
  if (name === 'appium_screenshot') {
    // Header of a 1206x2622 PNG followed by padding, wrapped the way appium-mcp wraps it (JSON in a text block).
    const header = Buffer.alloc(24);
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(header);
    header.writeUInt32BE(1206, 16);
    header.writeUInt32BE(2622, 20);
    const data = Buffer.concat([header, Buffer.alloc(3000, 7)]).toString('base64');
    return text(msg.id, JSON.stringify({ screenshot: { data, mimeType: 'image/png', filepath: '/tmp/appium-own-copy.png' } }));
  }
  if (name === 'appium_screenshot_structured' || name === 'appium_screenshot_file') {
    // The shapes appium-mcp really returns: structuredContent (MCP Apps clients) or, with NO_UI, only a path in text.
    const header = Buffer.alloc(24);
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(header);
    header.writeUInt32BE(1206, 16);
    header.writeUInt32BE(2622, 20);
    const bytes = Buffer.concat([header, Buffer.alloc(3000, 7)]);
    const filepath = require('path').join(require('os').tmpdir(), `fake-appium-shot-${process.pid}.png`);
    require('fs').writeFileSync(filepath, bytes);
    const textBlock = { type: 'text', text: `Screenshot saved successfully to: ${filepath}` };
    if (name === 'appium_screenshot_file') return send(msg.id, { content: [textBlock] });
    return send(msg.id, { content: [textBlock, { type: 'resource', resource: { uri: 'ui://x', mimeType: 'text/html', text: bytes.toString('base64') } }],
      structuredContent: { screenshot: { data: bytes.toString('base64'), mimeType: 'image/png', filepath } } });
  }
  if (name === 'appium_get_page_source') {
    return text(msg.id, 'Page source retrieved successfully: \n```xml <?xml version="1.0" encoding="UTF-8"?>\n<AppiumAUT>\n' +
      '<XCUIElementTypeApplication type="XCUIElementTypeApplication" name="Demo" label="Demo" enabled="true" visible="true" x="0" y="0" width="402" height="874" bundleId="com.example.demo">\n' +
      '<XCUIElementTypeWindow type="XCUIElementTypeWindow" enabled="true" visible="true" x="0" y="0" width="402" height="874">\n' +
      '<XCUIElementTypeOther type="XCUIElementTypeOther" enabled="true" visible="true" x="0" y="0" width="402" height="874">\n' +
      '<XCUIElementTypeButton type="XCUIElementTypeButton" name="save-btn" label="Save &amp; close" enabled="false" visible="true" x="10" y="20" width="100" height="40"/>\n' +
      '<XCUIElementTypeTextField type="XCUIElementTypeTextField" name="email" label="Email" value="a@b.c" enabled="true" visible="true" x="10" y="80" width="300" height="40"/>\n' +
      '<XCUIElementTypeStaticText type="XCUIElementTypeStaticText" name="hidden" label="Offscreen text" enabled="true" visible="false" x="0" y="900" width="100" height="20"/>\n' +
      '<XCUIElementTypeKeyboard type="XCUIElementTypeKeyboard" enabled="true" visible="true" x="0" y="600" width="402" height="270">\n' +
      '<XCUIElementTypeKey type="XCUIElementTypeKey" name="a" label="a" enabled="true" visible="true" x="0" y="600" width="30" height="40"/>\n' +
      '<XCUIElementTypeKey type="XCUIElementTypeKey" name="b" label="b" enabled="true" visible="true" x="30" y="600" width="30" height="40"/>\n' +
      '</XCUIElementTypeKeyboard>\n</XCUIElementTypeOther>\n</XCUIElementTypeWindow>\n</XCUIElementTypeApplication>\n</AppiumAUT>\n```');
  }
  if (name === 'image') return send(msg.id, { content: [{ type: 'image', data: expect, mimeType: 'image/png' }] });
  return text(msg.id, `ok ${name} ${JSON.stringify(args)}`);
});
