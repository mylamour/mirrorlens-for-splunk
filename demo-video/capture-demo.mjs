import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import fs from 'node:fs/promises';
import path from 'node:path';

const ROOT = path.resolve('.');
const OUT_DIR = path.join(ROOT, 'demo-video', 'frames');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9224 + Math.floor(Math.random() * 500);
const URL = 'http://127.0.0.1:8091';
const WIDTH = 1280;
const HEIGHT = 720;
const FPS = 2;
const DURATION_SECONDS = 125;

await fs.rm(OUT_DIR, { recursive: true, force: true });
await fs.mkdir(OUT_DIR, { recursive: true });
await fetch(`${URL}/api/demo/reset`, { method: 'POST' });

const profileDir = path.join('/tmp', `mirrorlens-chrome-video-${Date.now()}`);
const chrome = spawn(CHROME, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profileDir}`,
  '--no-first-run',
  '--no-default-browser-check',
  '--disable-gpu',
  '--hide-scrollbars',
  '--force-device-scale-factor=1',
  `--window-size=${WIDTH},${HEIGHT}`,
  'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] });

let closing = false;
async function cleanup() {
  if (closing) return;
  closing = true;
  chrome.kill('SIGTERM');
  await fs.rm(profileDir, { recursive: true, force: true }).catch(() => {});
}

process.on('exit', () => chrome.kill('SIGTERM'));
process.on('SIGINT', async () => {
  await cleanup();
  process.exit(130);
});

async function waitJson(url, timeoutMs = 10000) {
  const start = Date.now();
  let lastError;
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return await res.json();
    } catch (err) {
      lastError = err;
    }
    await delay(150);
  }
  throw lastError || new Error(`Timed out waiting for ${url}`);
}

await waitJson(`http://127.0.0.1:${PORT}/json/version`);
await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(URL)}`, { method: 'PUT' });
const tabs = await waitJson(`http://127.0.0.1:${PORT}/json/list`);
const pageTarget = tabs.find((tab) => tab.url === URL || tab.url === `${URL}/`) || tabs[0];
const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);

let nextId = 1;
const pending = new Map();
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(msg.error.message));
    else resolve(msg.result);
  }
};

await new Promise((resolve, reject) => {
  ws.addEventListener('open', resolve, { once: true });
  ws.addEventListener('error', reject, { once: true });
});

function cdp(method, params = {}) {
  const id = nextId++;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

async function evalPage(expression) {
  const result = await cdp('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || 'Runtime.evaluate failed');
  return result.result.value;
}

async function clickButton(text) {
  return evalPage(`(() => {
    const btn = [...document.querySelectorAll('button')]
      .find((b) => (b.innerText || '').includes(${JSON.stringify(text)}));
    if (!btn) return false;
    btn.click();
    return true;
  })()`);
}

async function scrollMain(top) {
  await evalPage(`window.scrollTo({ top: ${top}, behavior: 'smooth' }); true`);
}

async function capture(frameNumber) {
  const shot = await cdp('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
    captureBeyondViewport: false,
  });
  const file = path.join(OUT_DIR, `frame_${String(frameNumber).padStart(4, '0')}.png`);
  await fs.writeFile(file, Buffer.from(shot.data, 'base64'));
}

await cdp('Page.enable');
await cdp('Runtime.enable');
await cdp('Emulation.setDeviceMetricsOverride', {
  width: WIDTH,
  height: HEIGHT,
  deviceScaleFactor: 1,
  mobile: false,
});
await cdp('Page.navigate', { url: URL });

const loadStart = Date.now();
while (Date.now() - loadStart < 10000) {
  const ready = await evalPage('document.readyState');
  if (ready === 'complete') break;
  await delay(100);
}

console.log(`Capturing ${DURATION_SECONDS}s at ${FPS} fps...`);
let frame = 0;
let sampleClicked = false;
let traceOpened = false;
let scrolled = false;
let resetScroll = false;
let traceClosed = false;

const start = Date.now();
const totalFrames = DURATION_SECONDS * FPS;
while (frame < totalFrames) {
  const elapsed = (Date.now() - start) / 1000;

  if (!sampleClicked && elapsed >= 5) {
    sampleClicked = true;
    await fetch(`${URL}/api/demo/load`, { method: 'POST' });
  }

  if (!traceOpened && elapsed >= 78) {
    traceOpened = true;
    await clickButton('ACKNOWLEDGE');
    await delay(300);
    await clickButton('AGENT TRACE / MCP PROOF');
  }

  if (!traceClosed && elapsed >= 94) {
    traceClosed = true;
    await clickButton('CLOSE');
  }

  if (!scrolled && elapsed >= 98) {
    scrolled = true;
    await clickButton('ACKNOWLEDGE');
    await scrollMain(900);
  }

  if (!resetScroll && elapsed >= 116) {
    resetScroll = true;
    await scrollMain(0);
  }

  await capture(frame);
  if (frame % (FPS * 10) === 0) {
    console.log(`frame ${frame}/${totalFrames} (${Math.round(elapsed)}s)`);
  }
  frame += 1;

  const nextAt = start + (frame * 1000) / FPS;
  const sleepMs = Math.max(0, nextAt - Date.now());
  await delay(sleepMs);
}

ws.close();
await cleanup();

await fs.writeFile(path.join(ROOT, 'demo-video', 'capture-meta.json'), JSON.stringify({
  width: WIDTH,
  height: HEIGHT,
  fps: FPS,
  duration_seconds: DURATION_SECONDS,
  frames: totalFrames,
  out_dir: OUT_DIR,
}, null, 2));

console.log(`Done. Wrote ${totalFrames} frames to ${OUT_DIR}`);
