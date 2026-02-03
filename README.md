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
- **Google GenAI API Key:** Access to Gemini 2.0 Flash and Gemini 3.0 Pro.

### 2. Environment Configuration
SidecarAI is designed with a **Self-Healing Setup**. Simply launch the application:
```bash
python sidecar.py
```
If your `GOOGLE_API_KEY` is not found, the system will interactively guide you through the setup and generate your `.env` configuration automatically.

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
- **Engine:** Google Vertex/AI Studio (Gemini 2.0/3.0)
- **Capture:** `mss` (Multi-screen Screenshot)
- **Hooks:** Win32 API via `ctypes`
- **Logic:** Custom modular Python orchestration
