# Local install scripts

Run **one** of these from your machine (you can run it from anywhere; the script finds the repo root automatically):

| Platform | Script | How to run |
|----------|--------|------------|
| **macOS** | `install_mac.sh` | `./Install/install_mac.sh` or `bash Install/install_mac.sh` |
| **Linux** | `install_linux.sh` | `./Install/install_linux.sh` or `bash Install/install_linux.sh` |
| **Windows** | `install_windows.ps1` | In PowerShell: `.\Install\install_windows.ps1` (or right‑click → Run with PowerShell) |

Each script will:

1. Check for **Python 3.12 or higher** (and tell you how to install it if missing).
2. Install **uv** if it’s not already installed.
3. Create a **`.venv`** in the repo and run **`uv sync --frozen`** so all dependencies are installed.

After a successful run, activate the environment and start the app:

- **macOS/Linux:** `source .venv/bin/activate` then e.g. `uv run run_api`
- **Windows:** `.venv\Scripts\Activate.ps1` then e.g. `uv run run_api`

Or from the repo root without activating: `uv run run_api` or `uv run uvicorn agent.api:app --host 0.0.0.0 --port 5000`.
