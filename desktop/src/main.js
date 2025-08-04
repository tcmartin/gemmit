/* desktop/src/main.js  (CommonJS)
   ─────────────────────────────────────────────────────────────
   • On app start -> ensureGemini() installs / upgrades the CLI
   • Spawns the Python backend (PyInstaller one-file)
   • Waits for the HTTP health check (port 8001)
   • Opens a BrowserWindow
   • Wires in electron-updater
*/

const { app, BrowserWindow } = require('electron');
const { spawn, spawnSync }   = require('child_process');
const path                   = require('path');
const net                    = require('net');
const kill                   = require('tree-kill');
const fs                     = require('fs');
const os                     = require('os');
const { autoUpdater }        = require('electron-updater');

let backendProc;

/* ─── helpers ──────────────────────────────────────────────────────── */
function binDir () {
  if (process.platform === 'win32') return 'win';
  if (process.platform === 'darwin') return process.arch === 'arm64' ? 'mac-arm64' : 'mac-x64';
  return 'linux';
}

/* Wait until <host>:<port> accepts TCP connections */
function waitPort (port, host = '127.0.0.1') {
  return new Promise(resolve => {
    const timer = setInterval(() => {
      const sock = net.createConnection(port, host, () => {
        clearInterval(timer); sock.end(); resolve();
      });
      sock.on('error', () => sock.destroy());
    }, 250);
  });
}

/* ─── ONE-TIME per launch – make sure Gemini CLI is present ─────────── */
function ensureGemini () {
  const cacheDir = path.join(os.homedir(), '.vibe-gemini');
  const nodeBin  = path.join(process.resourcesPath, 'bin', binDir(),
                             process.platform === 'win32' ? 'node.exe' : 'node');
  const npmCli   = path.join(path.dirname(nodeBin), 'npm', 'bin', 'npm-cli.js');

  if (!fs.existsSync(nodeBin) || !fs.existsSync(npmCli)) {
    throw new Error('Embedded Node/npm runtime is missing; run fetch_node_runtimes.sh');
  }

  const env = {
    ...process.env,
    npm_config_prefix: cacheDir,                 // where npm puts bin/
    npm_config_update_notifier: 'false',
    npm_config_cache: path.join(cacheDir, '.npm-cache'),
  };

  /* Install/upgrade & sanity-check with --version */
  const r = spawnSync(nodeBin, [
    npmCli, 'exec', '--yes', '@google/gemini-cli@latest', '--', '--version'
  ], { env, stdio: 'ignore' });

  if (r.status !== 0) throw new Error('npm exec gemini-cli failed');

  return path.join(
    cacheDir,
    process.platform === 'win32' ? 'bin\\gemini.cmd' : 'bin/gemini'
  );
}

/* ─── start backend (Python) ───────────────────────────────────────── */
async function startBackend () {
  /* make GEMINI_PATH available to backend.py */
  process.env.GEMINI_PATH = ensureGemini();

  const exeName = process.platform === 'win32' ? 'backend.exe' : 'backend';
  const backendBin = path.join(process.resourcesPath, 'bin', binDir(), exeName);

  backendProc = spawn(backendBin, [], { stdio: 'ignore' });
  backendProc.once('exit', code => {
    console.error(`backend exited with code ${code}`); app.quit();
  });

  await waitPort(8001);        // backend HTTP health on 8001
}

/* ─── create window ───────────────────────────────────────────────── */
function createWindow () {
  const win = new BrowserWindow({ width: 1280, height: 800 });
  win.loadURL('http://127.0.0.1:8001/index.html');
}

/* ─── app lifecycle ───────────────────────────────────────────────── */
app.whenReady().then(async () => {
  await startBackend();
  createWindow();
  autoUpdater.checkForUpdatesAndNotify();
});

app.on('before-quit', () => {
  if (backendProc?.pid) kill(backendProc.pid);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

