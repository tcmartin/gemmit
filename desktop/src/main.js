/* desktop/src/main.js  (CommonJS)
   ─────────────────────────────────────────────────────────────
   • On app start -> ensureGemini() installs/upgrades the CLI (with logging)
   • Spawns the Python backend (one-file in prod, script in dev)
   • Waits for the HTTP health check (port 8001)
   • Opens a BrowserWindow
   • Wires in electron-updater
*/

const { app, BrowserWindow } = require('electron');
const { spawn, spawnSync } = require('child_process');
const path = require('path');
const net = require('net');
const kill = require('tree-kill');
const fs = require('fs');
const os = require('os');
const { autoUpdater } = require('electron-updater');

let backendProc;
let splashWindow;

/* ─── helpers ──────────────────────────────────────────────────────── */
function binDir() {
  if (process.platform === 'win32') return 'win';
  if (process.platform === 'darwin') return process.arch === 'arm64' ? 'mac-arm64' : 'mac-x64';
  return 'linux';
}
// ─── make sure our embedded node lives on PATH so "#!/usr/bin/env node" works ────────
if (app.isPackaged) {
    // path to your bundled node binary
    const nodeDirPath = path.join(process.resourcesPath, 'bin', binDir());
    // append it so system tools are found first, but node is still available
    process.env.PATH = `${process.env.PATH}${path.delimiter}${nodeDirPath}`;
  }
  

function waitPort(port, host = '127.0.0.1') {
  return new Promise(resolve => {
    const timer = setInterval(() => {
      const sock = net.createConnection(port, host, () => {
        clearInterval(timer); sock.end(); resolve();
      });
      sock.on('error', () => sock.destroy());
    }, 250);
  });
}

/* ─── check if Gemini CLI is authenticated ──────────────────────────── */
function isGeminiAuthenticated() {
  const settingsPath = path.join(os.homedir(), '.gemini', 'settings.json');
  return fs.existsSync(settingsPath);
}

/* ─── handle Gemini authentication at startup ──────────────────────── */
async function handleGeminiAuthentication(geminiPath) {
  return new Promise((resolve, reject) => {
    try {
      // Handle npx command properly
      let authCommand;
      if (geminiPath.startsWith('npx ')) {
        authCommand = `${geminiPath}`;
      } else {
        // For file paths, just run gemini without auth subcommand
        authCommand = `${geminiPath}`;
      }
      
      if (process.platform === 'win32') {
        // Windows: Open Command Prompt with gemini auth
        const { spawn } = require('child_process');
        spawn('cmd', ['/c', 'start', 'cmd', '/k', `${authCommand} && echo Authentication completed. You can close this window and return to Gemmit. && pause`], {
          detached: true,
          stdio: 'ignore'
        }).unref();
      } else if (process.platform === 'darwin') {
        // macOS: Use Terminal app
        const { spawn } = require('child_process');
        const script = `tell application "Terminal" to do script "${authCommand}; echo 'Authentication completed. You can close this window and return to Gemmit.'"`;
        spawn('osascript', ['-e', script], {
          detached: true,
          stdio: 'ignore'
        }).unref();
      } else {
        // Linux: Try common terminal emulators
        const { spawn } = require('child_process');
        const terminals = ['gnome-terminal', 'xterm', 'konsole', 'x-terminal-emulator'];
        let launched = false;
        
        for (const term of terminals) {
          try {
            if (term === 'gnome-terminal') {
              spawn(term, ['--', 'bash', '-c', `${authCommand}; echo 'Authentication completed. You can close this window and return to Gemmit.'; read -p 'Press Enter to close...'`], {
                detached: true,
                stdio: 'ignore'
              }).unref();
            } else {
              spawn(term, ['-e', `bash -c "${authCommand}; echo 'Authentication completed. You can close this window and return to Gemmit.'; read -p 'Press Enter to close...'""`], {
                detached: true,
                stdio: 'ignore'
              }).unref();
            }
            launched = true;
            break;
          } catch (e) {
            // Try next terminal
            continue;
          }
        }
        
        if (!launched) {
          console.warn('Could not find a suitable terminal emulator for authentication');
        }
      }
      
      // Give some time for the terminal to launch
      setTimeout(resolve, 1000);
      
    } catch (error) {
      console.error('Failed to launch authentication terminal:', error);
      reject(error);
    }
  });
}

/* ─── ONE-TIME per launch – ensure Gemini CLI via embedded Node/npm ──── */
async function ensureGemini() {
  updateSplashStatus('Setting up AI backend...');

  const cacheDir = path.join(os.homedir(), '.gemmit');
  // ensure prefix dirs exist
  if (!fs.existsSync(cacheDir)) fs.mkdirSync(cacheDir, { recursive: true });
  const prefixBin = path.join(cacheDir, 'bin');
  if (!fs.existsSync(prefixBin)) fs.mkdirSync(prefixBin, { recursive: true });
  const libModules = path.join(cacheDir, 'lib', 'node_modules');
  if (!fs.existsSync(libModules)) fs.mkdirSync(libModules, { recursive: true });

  // Check if Gemini CLI is already installed
  // On Windows, npm global installs put binaries in the prefix root
  // On Unix/macOS/Linux, npm global installs put binaries in prefix/bin
  const geminiPath = process.platform === 'win32'
    ? path.join(cacheDir, 'gemini.cmd')
    : path.join(prefixBin, 'gemini');

  if (fs.existsSync(geminiPath)) {
    updateSplashStatus('Gemini CLI found - checking authentication...');
    
    // Check authentication even if CLI is already installed
    if (!isGeminiAuthenticated()) {
      updateSplashStatus('Authentication required - opening auth window...');
      await handleGeminiAuthentication(geminiPath);
    }
    
    updateSplashStatus('AI backend ready!');
    return geminiPath;
  }

  updateSplashStatus('Installing Gemini CLI...');

  // In development, use system node/npm; in production, use embedded runtime
  let nodeBin, npmCli, nodeDir, env;
  
  if (app.isPackaged) {
    // Production: use embedded node/npm
    nodeBin = path.join(
      process.resourcesPath, 'bin', binDir(),
      process.platform === 'win32' ? 'node.exe' : 'node'
    );
    npmCli = path.join(path.dirname(nodeBin), 'npm', 'bin', 'npm-cli.js');
    if (!fs.existsSync(nodeBin) || !fs.existsSync(npmCli)) {
      throw new Error('Embedded Node/npm runtime is missing; run fetch_node_runtimes.sh');
    }
    nodeDir = path.dirname(nodeBin);
  } else {
    // Development: use system node/npm
    nodeBin = 'node';
    npmCli = null; // Will use 'npm' command directly
    nodeDir = null;
  }

  // Ensure we have a proper PATH that includes system tools for MCP servers
  const systemPath = process.env.PATH || (process.platform === 'win32' 
    ? 'C:\\Windows\\System32;C:\\Windows;C:\\Windows\\System32\\Wbem' 
    : '/usr/local/bin:/usr/bin:/bin');
  
  if (app.isPackaged && nodeDir) {
    env = {
      ...process.env,
      npm_config_prefix: cacheDir,
      npm_config_update_notifier: 'false',
      npm_config_cache: path.join(cacheDir, '.npm-cache'),
      // Include system PATH first so MCP servers can find npx, python, etc.
      PATH: `${systemPath}${path.delimiter}${nodeDir}`,
      // Also set NODE_PATH to help with module resolution
      NODE_PATH: path.join(nodeDir, '..', 'lib', 'node_modules'),
      // Ensure HOME is set (sometimes missing when launched from Finder)
      HOME: process.env.HOME || os.homedir(),
      // Set SHELL to bash for script execution
      SHELL: '/bin/bash',
    };
  } else {
    // Development: use system environment with npm prefix
    env = {
      ...process.env,
      npm_config_prefix: cacheDir,
      npm_config_update_notifier: 'false',
      npm_config_cache: path.join(cacheDir, '.npm-cache'),
      HOME: process.env.HOME || os.homedir(),
    };
  }

  // Debug logging to file
  const debugLog = `
Debug Info:
Current working directory: ${process.cwd()}
Node binary path: ${nodeBin}
Node directory in PATH: ${nodeDir}
npm-cli.js path: ${npmCli}
Node binary exists: ${fs.existsSync(nodeBin)}
npm-cli.js exists: ${fs.existsSync(npmCli)}
Full PATH: ${env.PATH}
process.resourcesPath: ${process.resourcesPath}
`;

  try {
    fs.writeFileSync(path.join(os.tmpdir(), 'gemmit-debug.log'), debugLog);
  } catch (e) {
    // Ignore debug log errors
  }



  updateSplashStatus('Installing Gemini CLI...');

  // Use appropriate npm command based on mode
  let r;
  if (app.isPackaged && npmCli) {
    // Production: Use embedded Node.js to run npm directly
    r = spawnSync(nodeBin, [
      npmCli, 'install', '--global', '@google/gemini-cli@latest'
    ], {
      env,
      stdio: ['ignore', 'pipe', 'pipe']
    });
  } else {
    // Development: Use system npm
    r = spawnSync('npm', [
      'install', '--global', '@google/gemini-cli@latest'
    ], {
      env,
      stdio: ['ignore', 'pipe', 'pipe']
    });
  }
  
  if (r.status !== 0) {
    console.error('npm install failed with status:', r.status);
    console.error('stdout:', r.stdout?.toString());
    console.error('stderr:', r.stderr?.toString());
    console.error('error:', r.error);
    throw new Error(`npm install gemini-cli failed with status ${r.status}; see previous logs`);
  }

  updateSplashStatus('Verifying installation...');

  // ② sanity-check with --version
  if (!fs.existsSync(geminiPath)) {
    throw new Error('Gemini CLI not found after install at ' + geminiPath);
  }
  r = spawnSync(geminiPath, ['--version'], { stdio: ['ignore', 'pipe', 'pipe'] });
  if (r.status !== 0) {
    console.error('❌ gemini --version failed');
    console.error('stdout:', r.stdout.toString());
    console.error('stderr:', r.stderr.toString());
    throw new Error('gemini --version failed; see logs above');
  }

  // ③ Check and handle authentication
  updateSplashStatus('Checking authentication...');
  if (!isGeminiAuthenticated()) {
    updateSplashStatus('Authentication required - opening auth window...');
    await handleGeminiAuthentication(geminiPath);
  }

  updateSplashStatus('AI backend ready!');
  return geminiPath;
}
/* ─── start backend (Python) ───────────────────────────────────────── */
async function startBackend() {
  let geminiPath;

  if (app.isPackaged) {
    updateSplashStatus('Preparing AI backend...');
    geminiPath = await ensureGemini();
    process.env.GEMINI_PATH = geminiPath;
    const exeName = process.platform === 'win32' ? 'backend.exe' : 'backend';

    const backendBin = path.join(process.resourcesPath, 'bin', binDir(), exeName);

    updateSplashStatus('Starting backend server...');

    // Set up proper environment for Python backend with full system access for MCP servers
    const backendEnv = {
      ...process.env,
      PATH: process.env.PATH || (process.platform === 'win32' 
        ? 'C:\\Windows\\System32;C:\\Windows;C:\\Windows\\System32\\Wbem' 
        : '/usr/local/bin:/usr/bin:/bin'),
      HOME: process.env.HOME || os.homedir(),
      TMPDIR: process.env.TMPDIR || os.tmpdir(),
      // Ensure Python can find system libraries
      DYLD_LIBRARY_PATH: process.env.DYLD_LIBRARY_PATH || '',
    };

    backendProc = spawn(backendBin, [], {
      stdio: ['ignore', 'inherit', 'inherit'],
      env: backendEnv
    });
  } else {
    console.log('⚙️  Dev mode: using local Python backend + npx gemini-cli');
    updateSplashStatus('Checking authentication...');
    
    // Use npx to run gemini CLI (no installation needed)
    geminiPath = 'npx @google/gemini-cli';
    
    // Check if authenticated and handle if not
    if (!isGeminiAuthenticated()) {
      updateSplashStatus('Authentication required - opening auth window...');
      await handleGeminiAuthentication(geminiPath);
    }
    
    updateSplashStatus('Starting development server...');
    process.env.GEMINI_PATH = geminiPath;

    // Set up proper environment for development backend with full system access for MCP servers
    const devBackendEnv = {
      ...process.env,
      PATH: process.env.PATH || (process.platform === 'win32' 
        ? 'C:\\Windows\\System32;C:\\Windows;C:\\Windows\\System32\\Wbem' 
        : '/usr/local/bin:/usr/bin:/bin'),
      HOME: process.env.HOME || os.homedir(),
      TMPDIR: process.env.TMPDIR || os.tmpdir(),
      GEMINI_PATH: geminiPath,
    };

    // In dev, server folder is one level up from desktop
    const script = path.join(process.cwd(), '..', 'server', 'backend.py');
    const pythonPath = process.env.PYTHON || (process.platform === 'win32' ? 
      path.join(process.cwd(), '..', 'server', '.venv', 'Scripts', 'python.exe') : 
      'python3');
    
    backendProc = spawn(pythonPath, [script], {
      stdio: ['ignore', 'inherit', 'inherit'],
      env: devBackendEnv
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
          document.getElementById('status').style.color = 'white';
        });
        ipcRenderer.on('splash-error', (event, error) => {
          document.getElementById('status').textContent = 'Error: ' + error;
          document.getElementById('status').style.color = '#ff6b6b';
          document.querySelector('.spinner').style.display = 'none';
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
function createWindow() {
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
  console.log('App is quitting, cleaning up processes...');
  if (backendProc?.pid) {
    console.log(`Killing backend process ${backendProc.pid}`);
    kill(backendProc.pid, 'SIGTERM');
    // Give it a moment, then force kill if needed
    setTimeout(() => {
      if (backendProc?.pid) {
        console.log(`Force killing backend process ${backendProc.pid}`);
        kill(backendProc.pid, 'SIGKILL');
      }
    }, 2000);
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Handle unexpected exits
process.on('exit', () => {
  if (backendProc?.pid) {
    kill(backendProc.pid, 'SIGKILL');
  }
});

process.on('SIGINT', () => {
  console.log('Received SIGINT, cleaning up...');
  if (backendProc?.pid) {
    kill(backendProc.pid, 'SIGTERM');
  }
  app.quit();
});

process.on('SIGTERM', () => {
  console.log('Received SIGTERM, cleaning up...');
  if (backendProc?.pid) {
    kill(backendProc.pid, 'SIGTERM');
  }
  app.quit();
});
