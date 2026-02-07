# SidecarAI

## Project Overview

**SidecarAI** is a high-performance, modular visual assistant designed for seamless, focus-preserving intelligence. It observes your active workflow and streams specialized analysis to a terminal interface via global hotkey triggers.

## Key Features

- **Modular Skill System:** Folder-based agent architecture with triple-layer prompting (Identity, Instructions, Context).
- **Dual-Vector Push Architecture:** Bypasses unreliable agentic tool-calling with direct context injection (Vector A: Visual, Vector B: Verbal).
- **Automated Verbal Pulse (v3.0):** High-speed, zero-latency speech-to-text pipeline with stateful "Start-Stop" recording.
- **Session Persistence:** "Zero-Touch" restoration of your cockpit configuration (Monitor, Mic, Engine, Skill).
- **Fast-Boot Sequence:** Get to **READY** state in <3 seconds without manual configuration.
- **Prompt Pivoting:** Hot-swap personas mid-session while maintaining full conversational history and state.
- **Conversational Transcription:** Spoken words act as the "most recent turn" in the conversation flow.
- **Extreme Speed Engine:** Groq Engine integration for sub-second reasoning and transcription using **Whisper-large-v3-turbo**.

---

## Technical Architecture

The project follows a modular Strategy Pattern designed for low-latency context injection.

### Directory Structure & Purpose

```text
.
├── core/                # Central logic package for all Sidecar services
│   ├── config/          # Environment resolution and hotkey/VK definitions
│   ├── drivers/         # Native Windows hooks for global keyboard listeners
│   ├── ingestion/       # Intake layer for screen capture and transcription polling
│   ├── intelligence/    # Orchestration layer for the "Push" architecture
│   │   └── engines/     # Hardware-abstracted AI Providers (Gemini & Groq)
│   ├── ui/              # CLI logic, branding, and status HUD management
│   └── utils/           # System bootstrapping, monitor detection, and setup
├── skills/              # Persona cartridges; defines identity and instructions
├── tests/               # Test suite for verifying context injection and event flows
└── sidecar.py           # Main cockpit orchestrator and entry point
```

- **Core Config**: Handles `.env` parsing and resolves absolute paths for project-wide assets.
- **Drivers**: Manages low-level `pywin32` hooks to ensure hotkeys work globally across applications.
- **Ingestion**: Handles Vector A (Pixel) via high-speed screen capture and Vector B (Talk) via a stateful `AudioSensor`. Direct-to-RAM recording using `sounddevice` ensures zero disk I/O and sub-300ms latency.
- **Intelligence**: The brain of the system. Manages state, chat history, and routes context to the active engine. Includes the `GroqTranscriptionEngine` for ultra-fast STT. Implements **Context Bloat Protection** by automatically pruning images in multi-turn conversations.
- **Engines**: Deeply optimized implementations for streaming text, images, and audio transcriptions using a unified event-driven model.
- **Skills**: A file-based system allowing users to define specialized agents (e.g., Coding, Debugging, Writing) that can be swapped mid-session.
- **UI & Utils**: Provides a premium terminal experience with a specialized status HUD and critical system utilities for environment setup.

---

## Usage & Controls

### Primary Vectors (`Ctrl + Alt + Shift + ...`)

| Key   | Vector      | Action        | Context Type                          |
| :---- | :---------- | :------------ | :------------------------------------ |
| **P** | **[P]ixel** | Analyze View  | Screenshot + Persistent Transcription |
| **T** | **[T]alk**  | Record Toggle | Transcription Follow-up (No Vision)   |
| **E** | **Engine**  | Switch Engine | Toggle between Gemini and Groq        |
| **S** | **Skill**   | Swap Skill    | Pivot model identity/instructions     |
| **M** | **Model**   | Toggle Model  | Toggle Fast/Deep models (Gemini)      |

## Transcription & Philosophy: The Conversational 'Now'

The **Transcription Guideline** is the **Current Moment** of the conversation. SidecarAI v3.0 introduces a high-speed "Pulse" architecture that captures raw hardware audio directly to RAM.

- **Stateful Recording**: Press `T` to begin recording (`[●] RECORDING...`). Press `T` again to finalize and push.
- **Zero-Latency Processing**: Audio is processed in memory and sent to Groq's `whisper-large-v3-turbo` model for near-instant transcription.
- **Shared Access**: Built on `sounddevice` (WASAPI), allowing Sidecar to maintain microphone access even if you are in a Zoom or Teams call.
- **Persistent Context**: [P]ixel captures include the transcription from your last communication as your "Current Guideline" (remains backward compatible with `transcription.txt` polling if enabled).
- **Active Intent**: [T]alk turns make the transcription the "Last Word" in the dialogue.
- **Verbal Interaction Protocol**: All follow-ups adhere to a "Pair-Programming Script" style—conversational, technical, and focused on concise bullet points.
- **Conversational Intelligence**: The model treats transcription as the "now" of the dialogue. If you end with a question, it answers. If you voice a mistake, it corrects it.

---

## Setup & Installation

### 1. Prerequisites

- **Windows OS:** (Required for native `pywin32` hooks).
- **Python 3.12+** (Recommended using `.venv`).
- **API Keys:** Google Gemini and/or Groq API keys.

### 2. Quick Start

```bash
# Install dependencies
.\.venv\Scripts\pip install -r requirements.txt

# Run the Sidecar in standard mode
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe sidecar.py

# Run with the Transparent Ghost Overlay
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe sidecar.py --ghost

# Run with Screenshot Debugging (saves captures to /debug_snapshots)
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe sidecar.py --debug
```

### 3. Special Execution Modes

#### **Ghost Mode (`--ghost`)**

Launches a transparent, always-on-top terminal overlay. This window is **invisible to screen capture** (e.g., Zoom, Teams, or regular screenshots) via the Win32 `SetWindowDisplayAffinity` protocol. You can move, resize, and scroll it via hotkeys or the minimalist scrollbar on the far right.

#### **Debug Mode (`--debug`)**

Enables the **Screenshot Debug Tool**. Every time you trigger a `[P]ixel` request, the raw image sent to the AI is saved in a project-root folder called `debug_snapshots/`. Use this to verify your monitor index and crop margins.

If keys are missing, the system will interactively guide you through the setup.

#### Advanced Configuration (`.env`)

| Key                  | Description                                          | Default                  |
| -------------------- | ---------------------------------------------------- | ------------------------ |
| `SIDECAR_ENGINE`     | Default engine (gemini, groq)                        | `gemini`                 |
| `GOOGLE_API_KEY`     | Your Google Gemini API Key                           | Optional                 |
| `MODEL_FLASH/PRO`    | Your Google Gemini Flash/Pro model names             | Optional                 |
| `GROQ_API_KEY`       | Your Groq API Key                                    | Optional                 |
| `GROQ_MODEL`         | The Maverick model for high speed                    | `llama-4-maverick...`    |
| `GROQ_STT_MODEL`     | Groq model for ultra-fast STT                        | `whisper-large-v3-turbo` |
| `PROJECT_ROOT`       | The base directory for the **Workspace Scanner**.    | `.`                      |
| `TRANSCRIPTION_PATH` | Path to the text file (Legacy support for Vector P). | `transcription.txt`      |

## Technology Stack

- **Reasoning Engine:** Google Gemini 1.5/2.0 (Deep Thinking)
- **Extreme Speed Engine:** Groq Cloud (Llama 3/4 Maverick)
- **Capture:** `mss` (Multi-screen Ultra-fast Screenshot)
- **Environment:** Python 3.12+ / Win32 API
- **Testing:** pytest with comprehensive context injection tests

## Testing

Run the test suite to verify context injection and event streaming:

```bash
pytest tests/ -v
```

Key test coverage:

- Context injection verification (Vector A + Vector B)
- Verbal stream delegation
- Transcription persistence logic
- Event streaming integrity
