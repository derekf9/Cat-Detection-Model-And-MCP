# Phase 1 — Pi Setup and Repo Skeleton

## Goal
Get the Pi running, the repo scaffolded, and Python working on every machine you'll develop on.

## Hardware Done
- [x] Pi 5, case, fan, power supply, 32GB SD card assembled
- [x] Pi is up and running (Raspberry Pi OS 64-bit, Bookworm)
- [ ] Camera module — have it, not installed yet

## Repo Done
- [x] Directory skeleton committed and pushed to GitHub
- [x] `.gitignore`, `requirements.txt`, `requirements-pi.txt`, `requirements-train.txt`, `requirements-dev.txt`
- [x] GitHub issues created for all 9 phases

## Python Setup — do this on each machine

### macOS
```bash
brew install python@3.11
git clone https://github.com/derekf9/Cat-Detection-Model-And-MCP.git
cd Cat-Detection-Model-And-MCP
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v   # should all pass
```

### Windows
1. Download Python 3.11 from https://python.org/downloads — check "Add Python to PATH"
2. Open PowerShell:
```powershell
git clone https://github.com/derekf9/Cat-Detection-Model-And-MCP.git
cd Cat-Detection-Model-And-MCP
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v
```

### Raspberry Pi (SSH in first)
```bash
git clone https://github.com/derekf9/Cat-Detection-Model-And-MCP.git
cd Cat-Detection-Model-And-MCP
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-pi.txt
```

## Done When
- [ ] `python -m pytest tests/ -v` passes on Mac or Windows
- [ ] SSH into Pi works and `python --version` shows 3.11+
- [ ] Camera module installed and visible to the OS (`libcamera-hello` shows a preview)
