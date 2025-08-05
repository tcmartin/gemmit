/* desktop/src/main.js  (CommonJS)
   ─────────────────────────────────────────────────────────────
   • On app start -> ensureGemini() installs/upgrades the CLI (with logging)
   • Spawns the Python backend (one-file in prod, script in dev)
   • Waits for the HTTP health check (port 8001)
   • Opens a BrowserWindow
   • Wires in electron-updater
*/

const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn, spawnSync }   = require('child_process');
const path                   = require('path');
const net                    = require('net');
const kill                   = require('tree-kill');
const fs                     = require('fs');
const os                     = require('os');
const { autoUpdater }        = require('electron-updater');

let backendProc;
let splashWindow;

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

/* ─── ONE-TIME per launch – ensure Gemini CLI via embedded Node/npm ──── */
function ensureGemini() {
  updateSplashStatus('Setting up AI backend...');
  
  const cacheDir = path.join(os.homedir(), '.gemmit');
  // ensure prefix dirs exist
  if (!fs.existsSync(cacheDir)) fs.mkdirSync(cacheDir, { recursive: true });
  const prefixBin = path.join(cacheDir, 'bin');
  if (!fs.existsSync(prefixBin)) fs.mkdirSync(prefixBin, { recursive: true });
  const libModules = path.join(cacheDir, 'lib', 'node_modules');
  if (!fs.existsSync(libModules)) fs.mkdirSync(libModules, { recursive: true });

  // Check if Gemini CLI is already installed
  const geminiPath = path.join(prefixBin, process.platform === 'win32'
    ? 'gemini.cmd' : 'gemini'
  );
  
  if (fs.existsSync(geminiPath)) {
    updateSplashStatus('AI backend ready!');
    return geminiPath;
  }

  updateSplashStatus('Installing Gemini CLI...');

  // locate embedded node/npm
  const nodeBin = path.join(
    process.resourcesPath, 'bin', binDir(),
    process.platform === 'win32' ? 'node.exe' : 'node'
  );
  const npmCli = path.join(path.dirname(nodeBin), 'npm', 'bin', 'npm-cli.js');
  if (!fs.existsSync(nodeBin) || !fs.existsSync(npmCli)) {
    throw new Error('Embedded Node/npm runtime is missing; run fetch_node_runtimes.sh');
  }

  const env = {
    ...process.env,
    npm_config_prefix:          cacheDir,
    npm_config_update_notifier: 'false',
    npm_config_cache:           path.join(cacheDir, '.npm-cache'),
    // Add the node binary directory to PATH so npm can find node
    PATH: `${path.dirname(nodeBin)}${path.delimiter}${process.env.PATH || ''}`,
  };

  updateSplashStatus('Downloading AI components...');

  // ① install globally into our prefix - use node directly to run npm-cli.js
  let r = spawnSync(nodeBin, [
    npmCli, 'install', '--global', '@google/gemini-cli@latest'
  ], { env, stdio: ['ignore','pipe','pipe'] });
  if (r.status !== 0) {
    console.error('npm install failed');
    console.error('stdout:', r.stdout?.toString());
    console.error('stderr:', r.stderr?.toString());
    throw new Error('npm install gemini-cli failed; see previous logs');
  }

  updateSplashStatus('Verifying installation...');

  // ② sanity-check with --version
  if (!fs.existsSync(geminiPath)) {
    throw new Error('Gemini CLI not found after install at ' + geminiPath);
  }
  r = spawnSync(geminiPath, ['--version'], { stdio: ['ignore','pipe','pipe'] });
  if (r.status !== 0) {
    console.error('❌ gemini --version failed');
    console.error('stdout:', r.stdout.toString());
    console.error('stderr:', r.stderr.toString());
    throw new Error('gemini --version failed; see logs above');
  }

  updateSplashStatus('AI backend ready!');
  return geminiPath;
}
/* ─── start backend (Python) ───────────────────────────────────────── */
async function startBackend () {
  if (app.isPackaged) {
    updateSplashStatus('Preparing AI backend...');
    process.env.GEMINI_PATH = ensureGemini();
    const exeName = process.platform === 'win32' ? 'backend.exe' : 'backend';
    
    const backendBin = path.join(process.resourcesPath, 'bin', binDir(), exeName);
    
    updateSplashStatus('Starting backend server...');
    backendProc = spawn(backendBin, [], { stdio: ['ignore','inherit','inherit'] });
  } else {
    console.log('⚙️  Dev mode: using local Python backend + global gemini-cli');
    updateSplashStatus('Starting development server...');
    process.env.GEMINI_PATH = 'gemini';
    // In dev, server folder is one level up from desktop
    const script = path.join(process.cwd(), '..', 'server', 'backend.py');
    backendProc = spawn(process.env.PYTHON || 'python3', [script], {
      stdio: ['ignore','inherit','inherit']
    });
  }

  backendProc.once('exit', code => {
    console.error(`backend exited with code ${code}`);
    app.quit();
  });

  updateSplashStatus('Waiting for server to start...');
  await waitPort(8001);
  updateSplashStatus('Loading application...');
}

/* ─── create splash screen ──────────────────────────────────────────── */
function createSplashScreen() {
  splashWindow = new BrowserWindow({
    width: 400,
    height: 300,
    frame: false,
    alwaysOnTop: true,
    transparent: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  // Use temp directory instead of trying to write to ASAR
  const tempDir = os.tmpdir();
  const splashPath = path.join(tempDir, 'gemmit-splash.html');
  
  // Get the correct icon path for both dev and production
  let iconPath;
  if (app.isPackaged) {
    // In production, icon is in the resources
    iconPath = path.join(process.resourcesPath, 'app', 'assets', 'icons', 'icon_128x128.png');
  } else {
    // In development
    iconPath = path.join(__dirname, '..', 'assets', 'icons', 'icon_128x128.png');
  }
  
  // Convert to file URL
  const iconUrl = `file://${iconPath.replace(/\\/g, '/')}`;
  
  // Create the splash HTML file
  const fs = require('fs');
  const splashHTML = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          margin: 0;
          padding: 20px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          height: 100vh;
          border-radius: 10px;
        }
        .logo-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          margin-bottom: 30px;
        }
        .logo-icon {
          width: 64px;
          height: 64px;
          margin-bottom: 15px;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .logo-text {
          font-size: 32px;
          font-weight: bold;
          margin: 0;
        }
        .tagline {
          font-size: 14px;
          opacity: 0.8;
          margin-top: 5px;
        }
        .status {
          font-size: 14px;
          margin-bottom: 10px;
          text-align: center;
        }
        .spinner {
          border: 2px solid rgba(255,255,255,0.3);
          border-radius: 50%;
          border-top: 2px solid white;
          width: 20px;
          height: 20px;
          animation: spin 1s linear infinite;
          margin: 10px;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      </style>
    </head>
    <body>
      <div class="logo-container">
        <img src="${iconUrl}" alt="Gemmit Logo" class="logo-icon" onerror="this.style.display='none'" />
        <div class="logo-text">Gemmit</div>
        <div class="tagline">AI-Powered Development Assistant</div>
      </div>
      <div class="status" id="status">Initializing...</div>
      <div class="spinner"></div>
      <script>
        const { ipcRenderer } = require('electron');
        ipcRenderer.on('splash-status', (event, message) => {
          document.getElementById('status').textContent = message;
        });
      </script>
    </body>
    </html>
  `;

  try {
    // Write the splash file to temp directory
    fs.writeFileSync(splashPath, splashHTML);
    splashWindow.loadFile(splashPath);
  } catch (error) {
    console.warn('Could not create splash file, using fallback:', error);
    // Fallback to data URL without icon
    const fallbackHTML = splashHTML.replace(/<img[^>]*>/, '');
    splashWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(fallbackHTML));
  }
  
  splashWindow.center();
  
  // Clean up the temporary file when splash closes
  splashWindow.on('closed', () => {
    try {
      if (fs.existsSync(splashPath)) {
        fs.unlinkSync(splashPath);
      }
    } catch (e) {
      // Ignore cleanup errors
    }
  });
}

function updateSplashStatus(message) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send('splash-status', message);
  }
}

function closeSplashScreen() {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.close();
    splashWindow = null;
  }
}

/* ─── create main window ───────────────────────────────────────────── */
function createWindow () {
  const win = new BrowserWindow({ 
    width: 1280, 
    height: 800,
    show: false // Don't show until ready
  });
  
  win.loadURL('http://127.0.0.1:8001/index.html');
  
  win.once('ready-to-show', () => {
    closeSplashScreen();
    win.show();
  });
  
  return win;
}

/* ─── app lifecycle ───────────────────────────────────────────────── */
app.whenReady().then(async () => {
  createSplashScreen();
  
  try {
    await startBackend();
    createWindow();
    
    try {
      await autoUpdater.checkForUpdatesAndNotify();
    } catch (e) {
      console.warn('Auto-update check failed (probably no GitHub releases yet):', e.message);
    }
  } catch (error) {
    updateSplashStatus('Error: ' + error.message);
    console.error('Startup error:', error);
    setTimeout(() => {
      app.quit();
    }, 3000);
  }
});

app.on('before-quit', () => {
  if (backendProc?.pid) kill(backendProc.pid);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
