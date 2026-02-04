# SidecarAI

## Project Overview

**SidecarAI** is a high-performance, modular visual assistant designed for seamless, focus-preserving intelligence. It observes your active workflow and streams specialized analysis to a terminal interface via global hotkey triggers.

## Key Features

- **Modular Skill System:** Folder-based agent architecture with triple-layer prompting (Identity, Instructions, Context).
- **Prompt Pivoting:** Hot-swap personas mid-session while maintaining full conversational history and state.
- **Stealth Visual Capture:** Passive screen observation with user-customizable crop margins for privacy and layout optimization.
- **Advanced Ingestion:** Integrated Notepad-bridge for clean ingestion of large datasets (codebase, logs, documentation).
- **Audio-Ready Pipeline:** Automated polling hooks for seamless integration with external transcription models (e.g., Whisper).
- **Dual Inference Engine:**
  - **Flash Mode:** Low-latency visual analysis.
  - **Pro Mode:** Advanced reasoning with active "Thinking" capabilities for complex logic.

## Technical Architecture

The project follows a decoupling-first approach with a minimal orchestrator pattern.

```text
SidecarAI/
├── core/                   # Internal Logic Package
│   ├── config/             # Application constants & environment
│   ├── drivers/            # OS-level hardware abstractions (Hotkeys)
│   ├── ingestion/          # Multi-modal data handling (Vision, Audio)
│   ├── intelligence/       # AI Engine & Skill management
│   ├── ui/                 # Terminal interaction layers
│   └── utils/              # Diagnostic & Setup utilities
├── skills/                 # User-defined Agent Personas (Cartridges)
│   ├── _template/          # Reference implementation blueprint
│   └── default/            # Active entry-point skill
├── sidecar.py              # Lean Orchestrator (Entry Point)
└── requirements.txt        # Dependency manifest
```

## Setup & Installation

### 1. Prerequisites

- **Windows OS:** (Required for native `pywin32` hotkey hooks).
- **Python 3.12+**
- **Google GenAI API Key:** Access to Gemini models.

### 2. Quick Start (The Wildcard)

To initialize the system, install dependencies, and launch the self-healing setup in one go:

```bash
pip install -r requirements.txt; $env:PYTHONPATH="."; .\.venv\Scripts\python.exe sidecar.py
```

If your `GOOGLE_API_KEY` is not found, the system will interactively guide you through the setup and generate your `.env` configuration automatically.

#### Advanced Configuration (`.env`)

You can fine-tune the application by editing the generated `.env` file:

| Key                      | Description                          | Default                  |
| ------------------------ | ------------------------------------ | ------------------------ |
| `GOOGLE_API_KEY`         | Your Google Gemini API Key           | Required                 |
| `SIDECAR_MONITOR_INDEX`  | Index of the monitor to capture      | `1`                      |
| `SIDECAR_CROP_TOP`       | Pixels to crop from the top          | `120`                    |
| `SIDECAR_CROP_BOTTOM`    | Pixels to crop from the bottom       | `40`                     |
| `HOTKEY_PROCESS`         | Primary key for "Analyze View"       | `P`                      |
| `HOTKEY_MODEL_TOGGLE`    | Primary key for "Toggle Model"       | `M`                      |
| `HOTKEY_SKILL_SWAP`      | Primary key for "Swap Skill"         | `S`                      |
| `MODEL_FLASH`            | The model ID for fast analysis       | `gemini-3-flash-preview` |
| `MODEL_PRO`              | The model ID for deep reasoning      | `gemini-3-pro-preview`   |
| `SIDECAR_THINKING_LEVEL` | "Thinking" depth (low, medium, high) | `high`                   |
| `SIDECAR_DEBUG`          | Save capture snapshots to disk       | `False`                  |

_Note: All hotkeys use the hardcoded modifier `Ctrl + Alt + Shift`._

### 3. Skill Customization

Each agent "Skill" resides in its own folder under `skills/` and is defined by three distinct layers:

- `identity.md`: The agent's persona and core behavior.
- `instructions.md`: Logical methodology and operational rules.
- `context.md`: Session-specific background knowledge (supports `{{PLACEHOLDER}}` variables).

## Usage & Interaction

### Standard Execution

```bash
python sidecar.py
```

### Global Hotkeys

- **Analyze View:** `Ctrl + Alt + Shift + P` (Process current screen view)
- **Toggle Model:** `Ctrl + Alt + Shift + M` (Switch between Flash & Pro Reasoning)
- **Swap Skill:** `Ctrl + Alt + Shift + S` (Trigger mid-conversation Pivot)

### Diagnostic Utilities

To verify your visual capture bounds and test crop margins:

```bash
python core/utils/debug_crop.py
```

Outputs are saved to the `debug_output/` directory for visual audit.

## Technology Stack

- **Engine:** Google Vertex/AI Studio (Gemini 3.0)
- **Capture:** `mss` (Multi-screen Screenshot)
- **Hooks:** Win32 API via `ctypes`
- **Logic:** Custom modular Python orchestration
