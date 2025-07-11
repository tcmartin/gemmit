# Gemmit AI Builder

**Gemmit** is a local AI-driven prototyping tool that lets you build frontend demos by chatting with a large language model (LLM). You can:

* **Write prompts** in a simple chat UI
* **Stream AI responses** in real time
* **Automatically spin up** a frontend preview server on a custom port
* **Save AI generation outputs** to a specified directory

---

## 📂 Directory Structure

```txt
/ (project root)
├── backend.py          # WebSocket server powering the AI chat & commands
├── index.html          # Landing page for Gemmit (HTML/CSS/JS)
├── chat.html           # Chat editor & preview page (HTML/CSS/JS)
└── README.md           # This file
```

> If you have a separate `frontend/` folder, move `index.html` and `chat.html` into it and open that folder in your browser.

---

## 🔧 Prerequisites

* **Python 3.7+**
* **gemini** CLI available (or adjust `GEMINI_PATH`)

Install required Python package:

```bash
pip install websockets
```

---

## 🚀 Running the Backend

From your project root, run:

```bash
# set environment variables, then start the backend
OUTPUT_DIR=./outputs \   # where AI generation files will be stored
GENERATIONS_DIR=./gens \ # (alias for OUTPUT_DIR)
GEMINI_PATH=gemini       # path to your gemini binary
python backend.py
```

* **OUTPUT\_DIR** and **GENERATIONS\_DIR** control where any files produced by your LLM process are written.
* **GEMINI\_PATH** tells the script which `gemini` executable to invoke.

The server listens on `ws://localhost:8000` by default.

---

## 🌐 Serving the Frontend

1. Open `index.html` in your browser (e.g. drag-and-drop or via a simple HTTP server).
2. Chat UI will appear. Enter a prompt and press **Send** (or click the ➤ button).
3. You’ll be redirected to `chat.html?prompt=…`, where the full chat interface lives.

**Optional:** If you’d like to serve via `http-server` (Node.js), run:

```bash
npm install -g http-server
http-server . -c-1
```

Then visit `http://localhost:8080/index.html`.

---

## ⚙️ Configuration via `window.APP_CONFIG`

You can inject defaults into the frontend by adding a small `<script>` block before other scripts in your HTML:

```html
<script>
  window.APP_CONFIG = {
    wsUrl: 'ws://localhost:8000',  // backend URL
    previewPort: 5002,             // default port for preview iframe
    generationsDir: './outputs',    // default output folder
    conversationId: 'conv-1234'     // optional persistent ID
  };
</script>
```

---

## ✨ Features

* **Streaming Chat**: Real-time token streaming from the LLM.
* **Preview Pane**: Live iframe preview of your generated frontend on a custom port.
* **Start Frontend**: Send a `start-frontend` command to spin up your dev server automatically.
* **Multi-command Payloads**: Pass `generationsDir` and `context` hints to the LLM.

---

## 📖 License

MIT © Your Name or Company

