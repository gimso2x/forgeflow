#!/usr/bin/env node
'use strict';

// Minimal dependency-free ForgeFlow Visual Companion.
// Serves a Mermaid browser page and accepts WebSocket text frames containing
// Mermaid diagram source from local agents/tools.

const http = require('http');
const crypto = require('crypto');

const PORT = Number(process.env.FORGEFLOW_VISUAL_PORT || process.env.PORT || 8765);
const clients = new Set();
let latestDiagram = 'flowchart TD\n  Start[ForgeFlow Visual Companion]\n  Start --> Waiting[Waiting for diagram updates]';

const page = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ForgeFlow Visual Companion</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    header { padding: 16px 20px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }
    main { padding: 20px; }
    #status { color: #93c5fd; font-size: 14px; }
    #diagram { background: #f8fafc; color: #0f172a; border-radius: 12px; padding: 24px; overflow: auto; }
    pre { white-space: pre-wrap; background: #020617; border: 1px solid #334155; border-radius: 8px; padding: 12px; }
  </style>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({ startOnLoad: false, theme: 'default' });
    const status = () => document.getElementById('status');
    const source = () => document.getElementById('source');
    const diagram = () => document.getElementById('diagram');
    async function render(text) {
      source().textContent = text;
      try {
        const id = 'diagram-' + Date.now();
        const rendered = await mermaid.render(id, text);
        diagram().innerHTML = rendered.svg;
        status().textContent = 'rendered ' + new Date().toLocaleTimeString();
      } catch (error) {
        diagram().textContent = String(error);
        status().textContent = 'render error';
      }
    }
    fetch('/diagram').then(r => r.text()).then(render);
    const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
    ws.onopen = () => { status().textContent = 'connected'; };
    ws.onmessage = event => render(event.data);
    ws.onclose = () => { status().textContent = 'disconnected'; };
  </script>
</head>
<body>
  <header>
    <strong>ForgeFlow Visual Companion</strong>
    <span id="status">loading</span>
  </header>
  <main>
    <section id="diagram"></section>
    <h2>Mermaid source</h2>
    <pre id="source"></pre>
  </main>
</body>
</html>`;

function sendFrame(socket, data) {
  const payload = Buffer.from(data);
  let header;
  if (payload.length < 126) {
    header = Buffer.from([0x81, payload.length]);
  } else if (payload.length < 65536) {
    header = Buffer.alloc(4);
    header[0] = 0x81;
    header[1] = 126;
    header.writeUInt16BE(payload.length, 2);
  } else {
    header = Buffer.alloc(10);
    header[0] = 0x81;
    header[1] = 127;
    header.writeBigUInt64BE(BigInt(payload.length), 2);
  }
  socket.write(Buffer.concat([header, payload]));
}

function decodeFrame(buffer) {
  if (buffer.length < 2) return '';
  const masked = (buffer[1] & 0x80) !== 0;
  let length = buffer[1] & 0x7f;
  let offset = 2;
  if (length === 126) {
    length = buffer.readUInt16BE(offset);
    offset += 2;
  } else if (length === 127) {
    length = Number(buffer.readBigUInt64BE(offset));
    offset += 8;
  }
  let mask;
  if (masked) {
    mask = buffer.subarray(offset, offset + 4);
    offset += 4;
  }
  const payload = buffer.subarray(offset, offset + length);
  if (!masked) return payload.toString('utf8');
  const decoded = Buffer.alloc(payload.length);
  for (let i = 0; i < payload.length; i += 1) decoded[i] = payload[i] ^ mask[i % 4];
  return decoded.toString('utf8');
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/') {
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    res.end(page);
    return;
  }
  if (req.method === 'GET' && req.url === '/diagram') {
    res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
    res.end(latestDiagram);
    return;
  }
  if (req.method === 'POST' && req.url === '/diagram') {
    const chunks = [];
    req.on('data', chunk => chunks.push(chunk));
    req.on('end', () => {
      latestDiagram = Buffer.concat(chunks).toString('utf8');
      for (const client of clients) sendFrame(client, latestDiagram);
      res.writeHead(204);
      res.end();
    });
    return;
  }
  res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
  res.end('not found\n');
});

server.on('upgrade', (req, socket) => {
  if (req.url !== '/ws') {
    socket.destroy();
    return;
  }
  const key = req.headers['sec-websocket-key'];
  const accept = crypto.createHash('sha1')
    .update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11')
    .digest('base64');
  socket.write('HTTP/1.1 101 Switching Protocols\r\n' +
    'Upgrade: websocket\r\n' +
    'Connection: Upgrade\r\n' +
    `Sec-WebSocket-Accept: ${accept}\r\n\r\n`);
  clients.add(socket);
  sendFrame(socket, latestDiagram);
  socket.on('data', data => {
    const text = decodeFrame(data);
    if (text.trim()) {
      latestDiagram = text;
      for (const client of clients) sendFrame(client, latestDiagram);
    }
  });
  socket.on('close', () => clients.delete(socket));
  socket.on('error', () => clients.delete(socket));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`ForgeFlow Visual Companion listening on http://127.0.0.1:${PORT}`);
});
