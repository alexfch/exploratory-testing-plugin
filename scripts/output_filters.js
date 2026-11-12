/*
 * output_filters.js: shrinks the big results of Appium tools before they reach the model.
 *
 * Used by secret_proxy.js (option --output-filters). Pure functions, no packages, Node 18+.
 *
 *   appium-screenshot     the tool returns a text result: JSON {"screenshot":{"data": <base64 PNG>, "filepath": ...}}.
 *                         A full-size PNG is 0.4-4 MB of text, which Claude Code refuses to inline and saves to a file,
 *                         so reading one screenshot used to take about three model turns. We return the file path plus
 *                         a small downscaled JPEG as a normal image block: one turn, a few hundred tokens.
 *   appium-page-source    the tool returns the whole accessibility tree as XML (tens of KB). We return a compact list of
 *                         the elements that are visible and carry a label, value or an interactive role, and save the
 *                         full XML to a file the Runner can grep.
 *
 * Every filter fails open: if the result does not look as expected it is returned unchanged.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const OUT_DIR = path.join(os.tmpdir(), 'exploratory-testing-mcp');

function ensureDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  return OUT_DIR;
}

function stamp() {
  return `${Date.now()}-${Math.floor(Math.random() * 1e4)}`;
}

function firstText(result) {
  const block = (result && result.content || []).find((b) => b && b.type === 'text' && typeof b.text === 'string');
  return block ? block.text : null;
}

// --------------------------------------------------------------------------- screenshot

function pngSize(buffer) {
  // PNG header: 8-byte signature, then the IHDR chunk; width and height are big-endian 32-bit at offsets 16 and 20.
  if (buffer.length < 24 || buffer.toString('ascii', 1, 4) !== 'PNG') return null;
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function downscaleToJpeg(pngFile, maxPx, quality) {
  if (process.platform !== 'darwin') return null; // sips ships with macOS; elsewhere we return the path only
  const jpgFile = pngFile.replace(/\.png$/, '.jpg');
  const run = spawnSync('sips', ['-Z', String(maxPx), '-s', 'format', 'jpeg', '-s', 'formatOptions', String(quality), pngFile, '--out', jpgFile],
    { stdio: 'ignore', timeout: 15000 });
  if (run.status !== 0 || !fs.existsSync(jpgFile)) return null;
  return jpgFile;
}

// appium-mcp can return a screenshot in four shapes, depending on the client's capabilities and its settings:
//   1. structuredContent.screenshot.data  (clients that support MCP Apps, which Claude Code does; the content is only a path text)
//   2. a text block holding JSON {"screenshot": {"data": ...}}
//   3. a text block "Screenshot saved successfully to: <path>" (with NO_UI=true; the PNG is only on disk)
//   4. an image block (returnRawBase64), often next to a huge embedded UI "resource" block with the same image as HTML
// We find the picture in any of them, and return a path plus a small preview.
function findScreenshot(result) {
  const sc = result.structuredContent && result.structuredContent.screenshot;
  if (sc && typeof sc.data === 'string' && sc.data.length >= 100) return { base64: sc.data, filepath: sc.filepath };
  let filepath;
  for (const block of result.content || []) {
    if (!block) continue;
    if (block.type === 'image' && typeof block.data === 'string' && block.data.length >= 100) return { base64: block.data, filepath };
    if (block.type === 'text' && typeof block.text === 'string') {
      const saved = block.text.match(/Screenshot saved successfully to:\s*(.+?)\s*$/m);
      if (saved) filepath = saved[1];
      if (block.text.includes('"data"')) {
        try {
          const parsed = JSON.parse(block.text);
          const shot = parsed.screenshot;
          if (shot && typeof shot.data === 'string' && shot.data.length >= 100) return { base64: shot.data, filepath: shot.filepath || filepath };
        } catch {
          // not JSON; keep looking
        }
      }
    }
  }
  if (filepath && fs.existsSync(filepath)) return { filepath };
  return null;
}

function shrinkScreenshot(result, opts = {}) {
  const maxPx = opts.maxImagePx || 900;
  const found = findScreenshot(result);
  if (!found) return result;

  let pngFile;
  let png;
  if (found.base64) {
    png = Buffer.from(found.base64, 'base64');
    pngFile = path.join(ensureDir(), `screenshot-${stamp()}.png`);
    fs.writeFileSync(pngFile, png);
  } else {
    pngFile = found.filepath; // the server already saved it
    png = fs.readFileSync(pngFile);
    ensureDir();
  }
  const size = pngSize(png);
  const sizeText = size ? `${size.width}x${size.height}px` : 'unknown size';

  const content = [];
  const jpgFile = downscaleToJpeg(pngFile, maxPx, opts.jpegQuality || 70);
  if (jpgFile) {
    content.push({
      type: 'text',
      text: `Screenshot saved: ${pngFile} (PNG, ${sizeText}). ` +
        `The image below is a downscaled preview (max ${maxPx}px) for looking at the screen. ` +
        'For pixel-exact checks, Read the PNG file. Do not call this tool again just to look at the same screen.',
    });
    content.push({ type: 'image', data: fs.readFileSync(jpgFile).toString('base64'), mimeType: 'image/jpeg' });
  } else {
    content.push({
      type: 'text',
      text: `Screenshot saved: ${pngFile} (PNG, ${sizeText}). No inline preview could be made on this machine; ` +
        'Read the file to look at it.',
    });
  }
  // structuredContent and _meta carried the full image (or a pointer to the HTML viewer); do not pass them on.
  const { structuredContent, _meta, ...rest } = result; // eslint-disable-line no-unused-vars
  return { ...rest, content };
}

// --------------------------------------------------------------------------- page source

const ENTITIES = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&apos;': "'" };

function decode(value) {
  return value
    .replace(/&(amp|lt|gt|quot|apos);/g, (m) => ENTITIES[m])
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&#x([0-9a-fA-F]+);/g, (_, n) => String.fromCodePoint(parseInt(n, 16)));
}

function parseAttrs(source) {
  const attrs = {};
  for (const m of source.matchAll(/([\w:.-]+)\s*=\s*"([^"]*)"/g)) attrs[m[1]] = decode(m[2]);
  return attrs;
}

// iOS element types that matter to a tester even without a label.
const IOS_INTERACTIVE = new Set(['Button', 'TextField', 'SecureTextField', 'TextView', 'SearchField', 'Switch', 'Slider',
  'Stepper', 'Picker', 'PickerWheel', 'DatePicker', 'Cell', 'Link', 'Tab', 'TabBar', 'SegmentedControl', 'NavigationBar',
  'Alert', 'Sheet', 'Toggle', 'Table', 'CollectionView', 'WebView', 'Keyboard', 'Menu', 'MenuItem', 'Popover']);

function describeIos(a) {
  const type = (a.type || '').replace(/^XCUIElementType/, '');
  const label = a.label || '';
  const name = a.name || '';
  const parts = [type];
  const text = label || name;
  if (text) parts.push(JSON.stringify(text));
  if (name && label && name !== label) parts.push(`id=${JSON.stringify(name)}`);
  if (a.value !== undefined && a.value !== '' && a.value !== text) parts.push(`value=${JSON.stringify(a.value)}`);
  if (a.enabled === 'false') parts.push('[disabled]');
  if (a.selected === 'true') parts.push('[selected]');
  if (a.x !== undefined) parts.push(`(${a.x},${a.y} ${a.width}x${a.height})`);
  return { type, text, line: parts.join(' ') };
}

function describeAndroid(a) {
  const cls = (a.class || '').split('.').pop();
  const text = a.text || a['content-desc'] || '';
  const parts = [cls];
  if (a.text) parts.push(JSON.stringify(a.text));
  if (a['content-desc']) parts.push(`desc=${JSON.stringify(a['content-desc'])}`);
  if (a['resource-id']) parts.push(`id=${a['resource-id']}`);
  if (a.checked === 'true') parts.push('[checked]');
  if (a.enabled === 'false') parts.push('[disabled]');
  if (a.bounds) parts.push(a.bounds);
  return { type: cls, text, line: parts.join(' ') };
}

function compactPageSource(result, opts = {}) {
  const maxChars = opts.maxChars || 12000;
  const text = firstText(result);
  if (!text) return result;
  const start = text.indexOf('<');
  if (start < 0 || !/<\/?[A-Za-z]/.test(text.slice(start, start + 200))) return result;
  const xml = text.slice(start).replace(/```\s*$/, '');

  const lines = [];
  const stack = []; // true when the open element was kept (to compute indentation)
  let total = 0;
  let keptCount = 0;
  let inKeyboard = 0;
  let keyCount = 0;

  for (const m of xml.matchAll(/<(\/?)([A-Za-z_][\w:.-]*)((?:[^>"']|"[^"]*"|'[^']*')*?)(\/?)>/g)) {
    const [, closing, tag, attrSource, selfClosing] = m;
    if (closing) {
      const wasKeyboard = stack.pop();
      if (wasKeyboard === 'keyboard') {
        inKeyboard -= 1;
        lines.push(`${'  '.repeat(stack.filter((s) => s === true).length + 1)}(${keyCount} keys not listed)`);
      }
      continue;
    }
    const attrs = parseAttrs(attrSource);
    const isIos = attrs.type && attrs.type.startsWith('XCUIElementType');
    const isAndroid = attrs.class !== undefined && attrs.bounds !== undefined;
    let mark = false;
    let line = '';
    if (isIos || isAndroid) total += 1;

    if (isIos) {
      const d = describeIos(attrs);
      if (d.type === 'Key' || d.type === 'Keyboard') {
        if (d.type === 'Key') keyCount += 1;
      }
      const visible = attrs.visible === 'true';
      const keepsMeaning = d.text || (attrs.value && attrs.value !== '') || IOS_INTERACTIVE.has(d.type);
      if (inKeyboard === 0 && visible && d.type !== 'Key' && d.type !== 'Application' && d.type !== 'Window' && keepsMeaning) {
        mark = true;
        line = d.line;
      }
      if (d.type === 'Keyboard' && !selfClosing) {
        inKeyboard += 1;
        keyCount = 0;
        stack.push('keyboard');
        if (mark) {
          lines.push(`${'  '.repeat(stack.slice(0, -1).filter((s) => s === true).length)}${line}`);
          keptCount += 1;
        }
        continue;
      }
      if (d.type === 'Application' && d.text) {
        mark = true;
        line = d.line; // one line for the app itself: its name and bundle
        if (attrs.bundleId) line += ` bundle=${attrs.bundleId}`;
      }
    } else if (isAndroid) {
      const d = describeAndroid(attrs);
      if (d.text || attrs.clickable === 'true' || attrs['resource-id'] || attrs.scrollable === 'true') {
        mark = attrs.displayed !== 'false';
        line = d.line;
      }
    }

    if (mark) {
      const depth = stack.filter((s) => s === true).length;
      lines.push(`${'  '.repeat(depth)}${line}`);
      keptCount += 1;
    }
    if (!selfClosing) stack.push(mark ? true : false);
  }

  if (total === 0) return result;

  const dir = ensureDir();
  const fullFile = path.join(dir, `page-source-${stamp()}.xml`);
  fs.writeFileSync(fullFile, xml);

  let body = lines.join('\n');
  let truncated = '';
  if (body.length > maxChars) {
    body = body.slice(0, maxChars);
    truncated = '\n... (list cut; the rest is in the full file)';
  }
  const header = `Page source, compact: ${keptCount} of ${total} elements (visible ones with a label, value or an interactive role). ` +
    `Full XML with every attribute: ${fullFile} (use Grep on it for anything not listed).\n` +
    'Line format: Type "label" id="accessibility id" value="..." [flags] (x,y widthxheight)\n';
  return { ...result, content: [{ type: 'text', text: `${header}${body}${truncated}` }] };
}

// --------------------------------------------------------------------------- registry

const FILTERS = {
  'appium-screenshot': shrinkScreenshot,
  'appium-page-source': compactPageSource,
};

function applyFilter(name, result, opts) {
  const filter = FILTERS[name];
  if (!filter || !result || result.isError || !Array.isArray(result.content)) return result;
  try {
    return filter(result, opts);
  } catch {
    return result; // fail open
  }
}

module.exports = { FILTERS, applyFilter, shrinkScreenshot, compactPageSource, pngSize, OUT_DIR };
