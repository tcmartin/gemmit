/* desktop/src/main.js
   Starts the bundled Python backend + gemini-cli,
   waits until the HTTP server is ready (port 8001),
   then opens a BrowserWindow, and wires in auto-updates. */

const { app, BrowserWindow } = require('electron');
const { spawn }              = require('child_process');
const path                   = require('path');
const net                    = require('net');
const kill                   = require('tree-kill');
const { autoUpdater }        = require('electron-updater');

let backendProc;   // will hold the child-process reference

// ---------- helpers ---------------------------------------------------------
function binDir () {
  switch (process.platform) {
    case 'win32':  return 'win';
    case 'darwin': return process.arch === 'arm64' ? 'mac-arm64' : 'mac-x64';
    default:       return 'linux';
  }
}

function waitPort (port, host = '127.0.0.1') {
  return new Promise(resolve => {
    const timer = setInterval(() => {
      const socket = net.createConnection(port, host, () => {
        clearInterval(timer);
        socket.end();
        resolve();
      });
      socket.on('error', () => socket.destroy());
    }, 250);
  });
}

// ---------- start backend ---------------------------------------------------
async function startBackend () {
  const exe  = process.platform === 'win32' ? 'backend.exe' : 'backend';
  const bin  = path.join(process.resourcesPath, 'bin', binDir(), exe);

  // Expose gemini-cli path to backend via env
  process.env.GEMINI_PATH = path.join(
    process.resourcesPath, 'bin', binDir(), process.platform === 'win32' ? 'gemini-cli.exe' : 'gemini-cli'
  );

  backendProc = spawn(bin, [], { stdio: 'ignore' });
  backendProc.once('exit', code => {
    console.error(`backend exited with code ${code}`);
    app.quit();
  });

  await waitPort(8001);   // backend serves HTTP on 8001 (/health checked internally)
}

// ---------- UI --------------------------------------------------------------
function createWindow () {
  const win = new BrowserWindow({ width: 1280, height: 800 });
  win.loadURL('http://127.0.0.1:8001/index.html');

  // Optional: open DevTools on ⌥⌘I / Ctrl+Shift+I
  // win.webContents.openDevTools();
}

// ---------- app lifecycle ---------------------------------------------------
app.whenReady().then(async () => {
  await startBackend();
  createWindow();
  autoUpdater.checkForUpdatesAndNotify();    // silent background updater
});

app.on('before-quit', () => {
  if (backendProc && backendProc.pid) kill(backendProc.pid);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

