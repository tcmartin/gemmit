/* desktop/src/main.js  (CommonJS)
   ─────────────────────────────────────────────────────────────
   • On app start -> ensureGemini() installs/upgrades the CLI (with logging)
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
  // Use ~/.gemmit as the npm install prefix
  const cacheDir = path.join(os.homedir(), '.gemmit');
  // Ensure the prefix directory exists
  if (!fs.existsSync(cacheDir)) fs.mkdirSync(cacheDir, { recursive: true });

  // Ensure lib/node_modules exists for npm installs
  const libModules = path.join(cacheDir, 'lib', 'node_modules');
  if (!fs.existsSync(libModules)) fs.mkdirSync(libModules, { recursive: true });

  const nodeBin = path.join(
    process.resourcesPath, 'bin', binDir(),
    process.platform === 'win32' ? 'node.exe' : 'node'
  );
  const npmCli = path.join(
    path.dirname(nodeBin), 'npm', 'bin', 'npm-cli.js'
  );

  if (!fs.existsSync(nodeBin) || !fs.existsSync(npmCli)) {
    throw new Error(
      'Embedded Node/npm runtime is missing; run fetch_node_runtimes.sh'
    );
  }

  const env = {
    ...process.env,
    npm_config_prefix:          cacheDir,                  // where npm puts bin/ & lib/
    npm_config_update_notifier: 'false',
    npm_config_cache:           path.join(cacheDir, '.npm-cache'),
  };

  // Install or upgrade the CLI, then immediately check --version
  const r = spawnSync(nodeBin, [
    npmCli, 'exec', '--yes', '@google/gemini-cli@latest', '--', '--version'
  ], { env, stdio: ['ignore', 'pipe', 'pipe'] });

  if (r.status !== 0) {
    console.error('❌ npm exec gemini-cli failed');
    console.error('--- stdout ---\n', r.stdout.toString());
    console.error('--- stderr ---\n', r.stderr.toString());
    throw new Error('npm exec gemini-cli failed; see logs above');
  }

  // Return the path to the installed gemini executable
  return path.join(
    cacheDir,
    process.platform === 'win32' ? 'bin\\gemini.cmd' : 'bin/gemini'
  );
}

/* ─── start backend (Python) ───────────────────────────────────────── */
async function startBackend () {
  // In packaged mode install+use embedded CLI; in dev you can point to global gemini
  if (app.isPackaged) {
    process.env.GEMINI_PATH = ensureGemini();
  } else {
    console.log('⚙️  Dev mode: using global gemini-cli');
    process.env.GEMINI_PATH = 'gemini';
  }

  const exeName = process.platform === 'win32' ? 'backend.exe' : 'backend';
  const backendBin = path.join(
    process.resourcesPath, 'bin', binDir(), exeName
  );

  backendProc = spawn(backendBin, [], { stdio: 'ignore' });
  backendProc.once('exit', code => {
    console.error(`backend exited with code ${code}`);
    app.quit();
  });

  await waitPort(8001);
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
