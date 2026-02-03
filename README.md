# SidecarAI

## Project Overview
**SidecarAI** is a stealthy, high-bandwidth visual assistant. It observes your active workflow on Monitor 1 and streams intelligence to Monitor 2 via a terminal interface, triggered by a global hotkey without ever stealing focus.

## Key Features
- **Stealth Capture:** Automatically crops browser tabs (top 120px) and taskbar (bottom 40px).
- **Zero-Focus:** Interaction triggers via global hotkey; output is standard stdout.
- **Dual AI Engine:**
    - **Flash Mode:** Uses `gemini-2.0-flash-exp` for instant, low-latency visual analysis.
    - **Pro Mode:** Uses `gemini-3.0-pro-preview` with **Low Thinking** enabled for complex reasoning and code analysis.

## Technology Stack
- **Language:** Python 3.12+
- **Screen Capture:** `mss`
- **Windows API:** `pywin32` (ctypes) for passive hotkeys.
- **AI SDK:** `google-genai` (Official Google Gen AI SDK v1 Beta).

## Setup & Installation

### 1. Prerequisites
- Windows OS (required for `pywin32`).
- Python 3.x installed.
- Access to Gemini 3.0 Pro Preview (for Pro mode).

### 2. Install Dependencies
Run the following command to install the required libraries:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory and add your Google API key:
```env
GOOGLE_API_KEY=AIzaSy...
```

## Usage

1.  **Start the application:**
    ```bash
    python main.py
    ```
2.  **Commands:**
    *   **Analyze View:** `Ctrl + Alt + Shift + P`
        *   Captures screen, sends to current model, streams text.
    *   **Toggle Model:** `Ctrl + Alt + Shift + M`
        *   Switches between **FLASH** (Fast) and **PRO** (Thinking).
    *   **Exit:** `Ctrl + C` in the terminal window.

## Troubleshooting
- **API Errors:** If you receive a 400 error regarding `thinking_level`, ensure you are using the `google-genai` SDK (not `google-generativeai` or `openai`) and that your API key has access to the preview models.
- **Hotkeys:** If the app says "Hotkey already in use," check if another instance or application is grabbing `Ctrl+Alt+Shift+P`.
