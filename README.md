# SidecarAI

## Project Overview

**SidecarAI** is a high-performance, modular visual assistant designed for seamless, focus-preserving intelligence. It observes your active workflow and streams specialized analysis to a terminal interface via global hotkey triggers.

## Key Features

- **Modular Skill System:** Folder-based agent architecture with triple-layer prompting (Identity, Instructions, Context).
- **Prompt Pivoting:** Hot-swap personas mid-session while maintaining full conversational history and state.
- **Stealth Visual Capture:** Passive screen observation with user-customizable crop margins for privacy and layout optimization.
- **Advanced Ingestion:** Integrated Notepad-bridge for clean ingestion of large datasets (codebase, logs, documentation).
- **Audio-Ready Pipeline:** Automated polling hooks for seamless integration with external transcription models (e.g., Whisper).
- **Multi-Engine Pipeline:**
  - **Gemini Engine:** High-accuracy reasoning with real-time "Thinking" summaries.
  - **Groq Engine:** Extreme-speed inference (500+ tok/s) using **Llama 4 Maverick**.

## Technical Architecture

The project follows a Strategy Pattern architecture for AI providers.

```text
SidecarAI/
├── core/                   # Internal Logic Package
│   ├── intelligence/       # AI Engines & Skill management
│   │   ├── engines/        # Provider Drivers (Gemini, Groq)
│   │   ├── model.py        # Engine Manager
│   │   └── skills.py       # Cartridge Loading
...
```

## Setup & Installation

### 1. Prerequisites

- **Windows OS:** (Required for native `pywin32` hotkey hooks).
- **Python 3.12+**
- **API Keys:** Google Gemini and/or Groq API keys.

### 2. Quick Start

```bash
pip install -r requirements.txt; $env:PYTHONPATH="."; .\.venv\Scripts\python.exe sidecar.py
```

If keys are missing, the system will interactively guide you through the setup.

#### Advanced Configuration (`.env`)

| Key                   | Description                       | Default               |
| --------------------- | --------------------------------- | --------------------- |
| `SIDECAR_ENGINE`      | Default engine (gemini, groq)     | `gemini`              |
| `GOOGLE_API_KEY`      | Your Google Gemini API Key        | Optional              |
| `GROQ_API_KEY`        | Your Groq API Key                 | Optional              |
| `HOTKEY_PROCESS`      | Primary key for "Analyze View"    | `P`                   |
| `HOTKEY_MODEL_TOGGLE` | Toggle Flash/Pro (Gemini only)    | `M`                   |
| `HOTKEY_SKILL_SWAP`   | Trigger mid-conversation Pivot    | `S`                   |
| `GROQ_MODEL`          | The Maverick model for high speed | `llama-4-maverick...` |

_Note: All hotkeys use the hardcoded modifier `Ctrl + Alt + Shift`._

## Usage & Interaction

### Global Hotkeys

- **Analyze View:** `Ctrl + Alt + Shift + P`
- **Toggle Engine:** `Ctrl + Alt + Shift + E` (Hot-swap between Gemini/Groq)
- **Toggle Model:** `Ctrl + Alt + Shift + M` (Gemini Flash/Pro Toggle)
- **Swap Skill:** `Ctrl + Alt + Shift + S` (Trigger Persona Pivot)

...

## Technology Stack

- **Engines:** Google Vertex/AI Studio, Groq Cloud
- **Models:** Gemini 3.0, Llama 4 Maverick 17B
- **Capture:** `mss` (Multi-screen Screenshot)
- **Hooks:** Win32 API via `ctypes`
