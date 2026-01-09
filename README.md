# Cortex Agent Desktop 🧠

The Cortex Agent is a professional-grade intelligence system acting as a bridge between **Telegram**, **Notion**, and **Google Gemini AI**. It uses a hybrid desktop architecture to provide real-time task extraction, deduplication, and context-aware intelligence.

![Version](https://img.shields.io/badge/version-0.1.0-blue) ![Stack](https://img.shields.io/badge/stack-Tauri%20%7C%20Python%20%7C%20Gemini-orange)

## 🏗️ Architecture

The application runs as a **Tauri** desktop app with a bundled **Python Sidecar**:

*   **Frontend (Tauri/Rust)**: Handles the OS window, system tray, and process lifecycle management. It launches and monitors the Python agent.
*   **Backend (Python Sidecar)**: The "Brain". Runs as a subprocess (`cortex-agent`).
    *   **Listener**: Connects to Telegram (MTProto) to intercept messages.
    *   **Agent**: Uses Google Gemini 2.0 to analyze message priority and extract tasks.
    *   **NotionSync**: Synchronizes high-priority items (P1-P3) to a Notion Database.
    *   **Server**: Exposes a local FastAPI implementation (Port 8000) for the UI dashboard.

## 🚀 Getting Started

### Prerequisites
*   Node.js & npm
*   Rust (Cargo)
*   Python 3.11+
*   Notion Integration Token & Database ID
*   Telegram API ID & Hash

### Installation

1.  **Clone & Install Dependencies**:
    ```bash
    git clone <repo>
    npm install
    ```

2.  **Setup Python Backend**:
    ```bash
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**:
    Create a `.env` file in `backend/` or rely on the Setup Wizard (first run) to create `~/.cortex/config.json`.

    **Key Variables**:
    *   `API_ID`, `API_HASH`: Telegram Auth
    *   `NOTION_TOKEN`, `NOTION_DATABASE_ID`: Notion Access
    *   `GENAI_KEY`: Google AI Key

## 🛠️ Development

To start the full stack (Tauri App + Python Sidecar):

```bash
npm run tauri dev
```

*   The Python binary is automatically rebuilt via `backend/build.py` if sources change.
*   Logs are written to `~/.cortex/cortex.log`.

## 🛡️ Key Features & Logic

### 1. Robust Deduplication 🏎️
The agent uses a **Hybrid Defense** strategy to prevent duplicate tasks:
*   **Layer 1 (Local Cache)**: An in-memory cache blocks duplicates instantly (0ms latency).
*   **Layer 2 (Verified Search)**: A synchronous check against Notion's `search` API ensures cross-session consistency, filtering out fuzzy matches manually.

### 2. Intelligent filtering 🧠
*   **Universal Outgoing Filter**: Ignores *all* messages sent by you (DMs & Groups) to prevent echo.
*   **Strict Triage**:
    *   **P1-P3**: Created as Notion Tasks.
    *   **P4 (Ignore)**: Polite chatter ("Thanks", "Ok") is logged to Audit but *never* creates a task.
    *   **P5 (Spam)**: Completely discarded.

### 3. Configurable "Catch-Up" ⚙️
To prevent a flood of old alerts on restart, the agent enforces a "Time Guard":
*   **Default**: Messages older than **120 seconds** are ignored.
*   **Configuration**: Change `CATCH_UP_SECONDS` in `~/.cortex/config.json` or via the Settings Dashboard.

## 📂 File Structure

```
cortex-desktop/
├── src-tauri/          # Rust/Tauri Core
├── src/                # Frontend Assets (Loading Screen)
├── backend/            # Python Source Code
│   ├── listener.py     # Telegram Event Loop
│   ├── agent.py        # Gemini AI Wrapper
│   ├── notion_sync.py  # Notion API Logic
│   ├── server.py       # FastAPI Dashboard Backend
│   └── build.py        # PyInstaller Build Script
└── README.md           # This file
```

## 🔐 Configuration & Security

The application stores your credentials (API keys, Session data) in:

**`~/.cortex/`** (Linux/macOS)

*   `config.json`: API Keys and settings.
*   `cortex.session`: Telegram Auth token.
*   `memory.json`: Long-term memory storage.

> [!WARNING]
> **Data is stored UNENCRYPTED**.
> This is standard for developer tools, but means any software running as your user can read these credentials.
> **Recommendation**: Run `chmod 600 ~/.cortex/config.json` to strictly limit permissions to your user only.

## ⚠️ Troubleshooting

**"App is damaged and can't be opened" (macOS)**
This occurs because the release is unsigned. Fix it by running:
```bash
xattr -cr /Applications/Cortex.app
```

**Logs & Debugging**
Logs are written to `~/.cortex/cortex.log`.
If the app crashes immediately on start (missing logs), run the binary manually to see the output:
```bash
/Applications/Cortex.app/Contents/MacOS/cortex-agent-*
```

**"Port 8000 already in use"**
*   The sidecar usually cleans up after itself via a **stdin watchdog** (if the parent app dies, the agent dies).
*   If it crashes hard, run `fuser -k 8000/tcp` (Linux) or `lsof -i :8000` (macOS) to find and kill the process.

**"ModuleNotFoundError" in Sidecar**
*   This usually means PyInstaller missed a file. Check `backend/build.py` and ensure the new module is added to `hiddenimports`.
