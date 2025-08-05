# Gemmit - AI-Powered Development Assistant

**Gemmit** is a cross-platform desktop application that combines the power of Google's Gemini AI with a streamlined development workflow. Built with Electron and Python, Gemmit provides an integrated environment for AI-assisted coding, project management, and rapid prototyping.

## 🚀 Key Features

- **Native Desktop App**: Cross-platform Electron application with native OS integration
- **AI-Powered Chat Interface**: Real-time streaming conversations with Gemini 2.5 Flash
- **Project Management**: Automatic project scaffolding in `~/Gemmit_Projects`
- **File Operations**: Built-in file browser, editor, and project management
- **Development Workflow**: Integrated with PocketFlow methodology for structured development
- **Auto-Updates**: Built-in update mechanism for seamless version management

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
```

## 🛠️ Development Setup

### Prerequisites

- **Node.js 18+** for Electron development
- **Python 3.8+** for backend services
- **Gemini CLI** installed and configured
- **macOS/Windows/Linux** (cross-platform support)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/tcmartin/gemmit.git
   cd gemmit
   ```

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

1. **Start the Electron app**
   ```bash
   cd desktop
   npm start
   ```

2. **Or run backend separately for debugging**
   ```bash
   cd server
   python backend.py
   ```

## 📦 Building for Production

### Build Desktop Application

```bash
cd desktop
npm run builder  # Creates platform-specific distributables
```

### Build Options

- **macOS**: Creates `.dmg` installer with proper code signing and entitlements
- **Windows**: Creates `.exe` installer with NSIS
- **Linux**: Creates AppImage for universal compatibility

### Distribution Files

Built applications are output to `desktop/dist/` with platform-specific formats:
- macOS: `gemmit-1.0.0.dmg`
- Windows: `gemmit Setup 1.0.0.exe`
- Linux: `gemmit-1.0.0.AppImage`

## 🔧 Configuration

### Environment Variables

- `GEMINI_PATH`: Path to Gemini CLI binary (default: `gemini`)
- `GENERATIONS_DIR`: Project workspace directory (default: `~/Gemmit_Projects`)
- `OUTPUT_DIR`: Output directory for generated files
- `PORT`: WebSocket server port (default: 8000)
- `HOST`: Server host address (default: 127.0.0.1)

### macOS Permissions

The app includes proper entitlements for:
- File system access to user directories
- Network client capabilities
- Home directory read/write permissions for project management

## 🎯 Usage Workflow

### 1. Project Initialization
- Launch Gemmit desktop app
- Projects are automatically created in `~/Gemmit_Projects/`
- AI guidelines and PocketFlow methodology are provisioned automatically

### 2. AI-Assisted Development
- Use the integrated chat interface to communicate with Gemini AI
- Real-time streaming responses with conversation history
- File operations (create, read, update) through the interface

### 3. Development Methodology
Gemmit follows the **PocketFlow** approach:
- **Requirements**: Human-driven requirement gathering
- **Design**: Collaborative high-level system design
- **Implementation**: AI-assisted coding with human oversight
- **Optimization**: Iterative improvement and testing

## 🔌 API Integration

### WebSocket API

The backend exposes a WebSocket API on `ws://localhost:8000` with support for:

- **Chat Operations**: Send prompts and receive streaming responses
- **File Operations**: List, read, and write project files
- **Conversation Management**: Persistent conversation history

### Example WebSocket Messages

```javascript
// Send a prompt
{
  "type": "prompt",
  "prompt": "Create a React component for user authentication",
  "conversationId": "conv-123"
}

// List project files
{
  "type": "list_files"
}

// Save a file
{
  "type": "save_file",
  "filename": "component.jsx",
  "content": "// React component code..."
}
```

## 🚢 Deployment

### Auto-Updates
- Built-in electron-updater integration
- Automatic update checks and installation
- GitHub releases integration for distribution

### Code Signing
- macOS: Proper entitlements and hardened runtime
- Windows: Authenticode signing support
- Cross-platform security best practices

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow the PocketFlow methodology outlined in `pocketflowguide.md`
- Ensure cross-platform compatibility
- Test on all supported platforms before submitting PRs
- Update documentation for new features

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Gemini**: AI model integration
- **Electron**: Cross-platform desktop framework
- **PocketFlow**: Development methodology framework
- **Open Source Community**: Various dependencies and tools

---

**Built with ❤️ by Trevor Martin**

For support, feature requests, or bug reports, please visit our [GitHub Issues](https://github.com/tcmartin/gemmit/issues) page.