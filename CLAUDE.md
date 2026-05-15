# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Raspberry Pi 5–based cat detection system that uses computer vision to identify Mimi (the cat), control a pet door via GPIO, and expose everything through a Model Context Protocol (MCP) server so Claude Desktop can answer natural-language queries ("Did Mimi go out today?") and manually lock/unlock the door.

See [ROADMAP.md](ROADMAP.md) for the full 9-phase development plan.

## Target Hardware

- Raspberry Pi 5 (4GB/8GB) running Raspberry Pi OS 64-bit (Bookworm)
- Pi Camera Module 3 (CSI) or USB webcam (OpenCV path)
- Coral USB Accelerator (optional but strongly recommended for inference speed)
- 1x green LED + 1x red LED + 2x 330Ω resistors wired to GPIO 27 (green) and GPIO 17 (red)

## Architecture

```
Cat-Detection-Model-And-MCP/
├── capture/          # SourceController abstraction + PiCamera/Webcam/VideoFile sources
│                     # capture_motion.py: frame-diff motion detection loop
├── detection/        # YOLOv8n species classifier (cat/dog/person/other)
├── classifier/       # Fine-tuned Mimi identity model (fastai / HuggingFace)
├── door/             # DoorController abstraction + Console/LED/Servo implementations
├── storage/          # SQLite persistence (detections, door events, metadata)
├── mcp_server/       # Python MCP server (SSE) — tools for Claude Desktop
├── services/
│   ├── dashboard_api/  # FastAPI: detection data + stats as JSON
│   └── video_api/      # FastAPI: signed cloud video URLs
├── dashboard/        # JS frontend (React or Svelte) — Phase 9
├── data/
│   ├── snapshots/    # Runtime capture output — gitignored
│   ├── test/         # Mimi test video clips — gitignored
│   └── training/     # Labeled training images — gitignored
└── tests/
    ├── capture/      # Tests for capture/
    └── door/         # Tests for door/
```

### Key Data Flow

1. `capture/` grabs frames; frame-differencing triggers on motion.
2. Motion frames → `detection/` — YOLOv8n labels species.
3. Cat frames → `classifier/` — fine-tuned model identifies Mimi vs unknown cat.
4. Mimi near the door zone → `door/` — auto-unlocks (green LED), re-locks after timeout.
5. All events written to SQLite via `storage/`.
6. `mcp_server/` exposes MCP tools over SSE so Claude Desktop can query history and control the door.

### Video Source Strategy

The `SourceController` abstraction in `capture/source.py` decouples the pipeline from hardware:

| Platform | Command flag | Implementation |
|----------|-------------|----------------|
| Raspberry Pi | `--source pi` | `PiCameraSource` (picamera2) |
| Mac/Windows webcam | `--source webcam` | `WebcamSource` (OpenCV) |
| Mac/Windows dev/test | `--source file --path data/test/mimi_morning.mp4` | `VideoFileSource` |

### Door Controller Strategy

The `DoorController` abstraction in `door/door_controller.py` mirrors the same pattern:

| Environment | Class | Notes |
|-------------|-------|-------|
| Any OS (dev) | `ConsoleDoorController` | Logs locked/unlocked — no hardware needed |
| Raspberry Pi | `LEDDoorController` | Red/green GPIO LEDs (gpiozero) |
| Future (Phase 9+) | `ServoDoorController` | Physical latch — not yet implemented |

### MCP Server Tools (Phase 7+)

| Tool | Description |
|------|-------------|
| `get_recent_detections` | Latest N detection events with timestamps |
| `get_snapshot` | Return a specific image by detection ID |
| `get_cat_status` | Current inside/outside status |
| `get_stats` | Aggregate stats over a time range |
| `unlock_door` | Unlock for N seconds then auto-relock |
| `lock_door` | Immediately lock, cancels any timeout |
| `get_door_status` | Current locked/unlocked state + seconds remaining |
| `get_door_patterns` | Ingress/egress insights from SQLite history |

## Development Setup

### Prerequisites: Python 3.11

**macOS:**
```bash
brew install python@3.11
```

**Windows:**
Download the installer from https://python.org/downloads — check "Add Python to PATH".

**Linux / Raspberry Pi:**
```bash
sudo apt update && sudo apt install python3.11 python3.11-venv python3.11-pip
```

### Local setup (Mac / Windows / Linux — not Pi)

```bash
git clone https://github.com/derekf9/Cat-Detection-Model-And-MCP.git
cd Cat-Detection-Model-And-MCP

python3.11 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt -r requirements-dev.txt
```

### Pi setup (SSH in first)

```bash
git clone https://github.com/derekf9/Cat-Detection-Model-And-MCP.git
cd Cat-Detection-Model-And-MCP
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-pi.txt
```

### Running tests

```bash
# All tests
python -m pytest tests/ -v

# Single module
python -m pytest tests/capture/ -v
python -m pytest tests/door/ -v

# With coverage report
python -m pytest tests/ --cov=. --cov-report=term-missing
```

## Development Workflow

- **Training (Phase 5):** runs on laptop or Google Colab (free GPU) — not on the Pi.
  Copy the resulting model to the Pi via `scp classifier/model.pkl pi@<pi-ip>:~/cat-cam/classifier/`
- **Inference + MCP server:** run on the Pi. Connect via SSH for all Pi-side work.
- **Test video clips:** record on Pi, store in `data/test/` (gitignored), use with `VideoFileSource` on Mac/Windows.

## Key Dependencies

| Package | Requirements file | Purpose |
|---------|------------------|---------|
| `opencv-python-headless` | requirements.txt | Frame capture + motion diff |
| `ultralytics` | requirements.txt | YOLOv8n detection |
| `mcp` | requirements.txt | MCP server SDK |
| `fastapi` + `uvicorn` | requirements.txt | Microservice APIs (Phase 9) |
| `picamera2` | requirements-pi.txt | CSI camera on Pi |
| `gpiozero` | requirements-pi.txt | GPIO LED control |
| `onnxruntime` | requirements-pi.txt | Optimised inference on Pi |
| `torch` + `fastai` | requirements-train.txt | Model training (laptop/Colab) |
| `pytest` + `pytest-cov` | requirements-dev.txt | Test suite |
