
<div align="center">
  <img src="assets/logos/gemmit-logo-128.png" alt="Gemmit Logo" width="128" height="128">
  <h1>Gemmit - AI-Powered Development Assistant</h1>
</div>

**Completely Free & No Vendor Lock-In**

- Runs entirely off Google's **Gemini CLI**—no local model downloads or OpenAI API keys required.
- 100% local environment: your code and projects stay on your machine in `~/Gemmit_Projects`.
- No vendor lock-in: build, customize, and extend however you like.
- Scoped by default: Gemmit automatically “scopes out” tasks, analyzes your project, and proposes context-aware actions.

**Seamless Mobile Integration**

- Works with [gemmit-app](https://github.com/tcmartin/gemmit-app) for on-the-go AI edits and project management from your phone.

## 🚀 Key Features

- **AI-Powered Chat Interface**: Real-time streaming conversations with Gemini 2.5 Flash over WebSockets.
- **Project Scaffolding**: Automatic creation of new projects under `~/Gemmit_Projects` following the PocketFlow methodology.
- **File Operations**: Browse, create, read, update, and delete files directly in-app.
- **Scoped Intelligence**: AI introspects your existing codebase and suggests context-aware changes.
- **Model Context Protocol (MCP) Support**: Configure custom M(odel)C(ontext)P(ipeline) servers via `.gemmit/settings.json`.
- **Extensible CLI Core**: Leverage the full power of `gemini-cli` under the hood—swap in any Gemini-based model.
- **Auto-Updates**: Built-in GitHub Releases integration for seamless version management.
- **Cross-Platform**: Packaged for macOS (Intel & Apple Silicon), Windows, and Linux.

## 📁 Project Architecture

```

gemmit/
├── desktop/                    # Electron frontend application
│   ├── src/                   # Main Electron process and renderer
│   ├── assets/                # Icons and static assets
│   ├── build/                 # Build configurations and entitlements
│   ├── resources/             # Bundled resources (binaries, etc.)
│   └── electron-builder.yaml  # Build configuration
├── server/                    # Python backend service
│   ├── backend.py            # WebSocket server and AI integration
│   └── requirements.txt      # Python dependencies
├── app/                      # Web UI components
│   ├── index.html           # Main application interface
│   └── chat.html            # Chat interface
├── scripts/                  # Build and deployment scripts
│   ├── build_backend.sh     # Backend compilation script
│   └── prepare_tree.sh      # Project setup utilities
├── ai_guidelines.md         # AI assistant behavior guidelines
└── pocketflowguide.md      # Development methodology guide

````

## 🛠️ Development Setup

### Prerequisites

- **Node.js 18+** for Electron development
- **Python 3.8+** for backend services
- **Gemini CLI** installed (automatically handled by gemmit)
- **macOS/Windows/Linux** (cross-platform support)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/tcmartin/gemmit.git
   cd gemmit
````

2. **Install desktop dependencies**

   ```bash
   cd desktop
   npm install
   ```
3. **Install Python dependencies**

   ```bash
   cd ../server
   pip install -r requirements.txt
   ```
4. **Build the backend binary**

   ```bash
   cd ../scripts
   ./build_backend.sh
   ```

### Running in Development

* **Start the Electron app**

  ```bash
  cd desktop
  npm start
  ```
* **Or run backend separately for debugging**

  ```bash
  cd server
  python backend.py
  ```

## 📦 Building for Production

### Build Desktop Application

```bash
cd desktop
npm run builder
```

### Build Targets

* **macOS**: `.dmg` installer (Intel & Apple Silicon)
* **Windows**: `.exe` installer (NSIS)
* **Linux**: AppImage and `.deb` for Debian/Ubuntu

### Distribution Files

Built apps output to `desktop/dist/` with names like:

* `gemmit-1.0.3.dmg`
* `gemmit-1.0.3-arm64.dmg`
* `gemmit Setup 1.0.3.exe`
* `gemmit-1.0.3.AppImage`
* `desktop_1.0.3_amd64.deb`

## 🔧 Configuration & Environment Variables

| Variable          | Description                      | Default                   |
| ----------------- | -------------------------------- | ------------------------- |
| `GEMINI_PATH`     | Path to your `gemini` CLI binary | `gemini`                  |
| `GENERATIONS_DIR` | Workspace root for projects      | `~/Gemmit_Projects`       |
| `OUTPUT_DIR`      | Directory for generated assets   | same as `GENERATIONS_DIR` |
| `PORT`            | WebSocket server port            | `8000`                    |
| `HOST`            | Server host address              | `127.0.0.1`               |

## 🗂️ Model Context Protocol Example

Create a `.gemini/settings.json` file *inside* your `~/Gemmit_Projects/.gemini/` folder:

```json
{
  "theme": "GitHub",
  "mcpServers": {
    "imagegen": {
      "command": "npx",
      "args": ["imagegen-mcp", "--models", "gpt-image-1"],
      "env": {
        "OPENAI_API_KEY": "<your key or env var>"
      }
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  },
  "hideTips": false
}
```

This tells Gemmit how to spin up external MCP servers for image generation, automated end-to-end testing, or anything else you can script.

## 📥 Installation for Users

### macOS

1. Download the appropriate `.dmg` from [Releases](https://github.com/tcmartin/gemmit/releases)
2. Open and drag Gemmit to Applications
3. If you see “Gemmit is damaged”, run:

   ```bash
   sudo xattr -rd com.apple.quarantine /Applications/Gemmit.app
   ```
4. Or use our helper script:

   ```bash
   curl -sSL https://raw.githubusercontent.com/tcmartin/gemmit/master/scripts/fix_macos_gatekeeper.sh | bash
   ```

### Windows

1. Download the Setup `.exe` from [Releases](https://github.com/tcmartin/gemmit/releases)
2. Run the installer (ignore SmartScreen warnings)

### Linux

* **AppImage**:

  ```bash
  chmod +x gemmit-1.0.3.AppImage
  ./gemmit-1.0.3.AppImage
  ```
* **DEB**:

  ```bash
  sudo dpkg -i desktop_1.0.3_amd64.deb
  ```

## 🎯 Usage Workflow

1. **Initialize**: Launch Gemmit, point it at or create a project in `~/Gemmit_Projects/`.
2. **Scope**: Gemmit analyzes your code and suggests next steps.
3. **Chat**: Use the built-in chat UI to prompt Gemini for code, docs, or tests.
4. **File Ops**: Modify, save, or generate new files—all from within the app.
5. **Iteration**: Repeat with PocketFlow methodology—design, implement, optimize.

## 🔌 WebSocket API

**Endpoint**: `ws://localhost:8000`

### Chat Prompt

```json
{ "type": "prompt", "prompt": "Generate a React login form", "conversationId": "abc-123" }
```

### File Listing

```json
{ "type": "list_files" }
```

### Save File

```json
{ "type": "save_file", "filename": "LoginForm.jsx", "content": "<code>" }
```

## 🚢 Deployment & Auto-Updates

* Uses `electron-updater` for background update checks.
* Releases hosted on GitHub trigger installer downloads.

## 🤝 Contributing

1. Fork, branch, code, PR.
2. Follow PocketFlow in `pocketflowguide.md`.
3. Test on all platforms.

## 📄 License

MIT. See [LICENSE](LICENSE).

## 🙏 Acknowledgments

* **Google Gemini**
* **Electron**
* **PocketFlow**
* **Open Source Community**

---

**Built with ❤️ by Trevor Martin**

For support, feature requests, or bug reports, please visit our [GitHub Issues](https://github.com/tcmartin/gemmit/issues) page.

## ☕ Support the Project

If you find Gemmit helpful, consider supporting its development:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow.svg?style=flat-square&logo=buy-me-a-coffee)](https://buymeacoffee.com/tcmartin)