# SidecarAI

## Project Overview

**SidecarAI** is a high-performance, modular visual assistant designed for seamless, focus-preserving intelligence. It observes your active workflow and streams specialized analysis to a terminal interface via global hotkey triggers.

## Key Features

- **Modular Skill System:** Folder-based agent architecture with triple-layer prompting (Identity, Instructions, Context).
- **Dual-Vector Push Architecture:** Bypasses unreliable agentic tool-calling with direct context injection (Vector A: Visual, Vector B: Verbal).
- **Prompt Pivoting:** Hot-swap personas mid-session while maintaining full conversational history and state.
- **Conversational Transcription:** Spoken words act as the "most recent turn" in the conversation flow.
- **Extreme Speed Engine:** Groq Engine integration for sub-second reasoning using **Llama 4 Maverick**.

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
- **Ingestion**: Handles Vector A (Pixel) via high-speed screen capture and Vector B (Talk) by polling external transcription streams. Uses in-place truncation to ensure `transcription.txt` stability for external watchers.
- **Intelligence**: The brain of the system. Manages state, chat history, and routes context to the active engine. Implements **Context Bloat Protection** by automatically pruning images in multi-turn conversations.
- **Engines**: Deeply optimized implementations for streaming text and images to LLMs using a unified event-driven model.
- **Skills**: A file-based system allowing users to define specialized agents (e.g., Coding, Debugging, Writing) that can be swapped mid-session.
- **UI & Utils**: Provides a premium terminal experience with a specialized status HUD and critical system utilities for environment setup.

---

## Usage & Controls

### Primary Vectors (`Ctrl + Alt + Shift + ...`)

| Key   | Vector      | Action        | Context Type                          |
| :---- | :---------- | :------------ | :------------------------------------ |
| **P** | **[P]ixel** | Analyze View  | Screenshot + Persistent Transcription |
| **T** | **[T]alk**  | Verbal Turn   | Transcription Follow-up (No Vision)   |
| **E** | **Engine**  | Switch Engine | Toggle between Gemini and Groq        |
| **S** | **Skill**   | Swap Skill    | Pivot model identity/instructions     |
| **M** | **Model**   | Toggle Model  | Toggle Fast/Deep models (Gemini)      |

## Transcription & Philosophy: The Conversational 'Now'

The **Transcription Guideline** is the **Current Moment** of the conversation.

- **Persistent Context**: [P]ixel captures include the transcription from your last communication as your "Current Guideline".
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

# Run the Sidecar
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe sidecar.py
```

If keys are missing, the system will interactively guide you through the setup.

#### Advanced Configuration (`.env`)

| Key                  | Description                                                         | Default               |
| -------------------- | ------------------------------------------------------------------- | --------------------- |
| `SIDECAR_ENGINE`     | Default engine (gemini, groq)                                       | `gemini`              |
| `GOOGLE_API_KEY`     | Your Google Gemini API Key                                          | Optional              |
| `MODEL_FLASH/PRO`    | Your Google Gemini Flash/Pro model names                            | Optional              |
| `GROQ_API_KEY`       | Your Groq API Key                                                   | Optional              |
| `GROQ_MODEL`         | The Maverick model for high speed                                   | `llama-4-maverick...` |
| `PROJECT_ROOT`       | The base directory for the **Workspace Scanner**.                   | `.`                   |
| `TRANSCRIPTION_PATH` | Path to the text file where your meeting transcriptions are stored. | `transcription.txt`   |

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
