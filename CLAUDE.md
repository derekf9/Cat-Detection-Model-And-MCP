# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Raspberry Pi–based cat detection system that uses computer vision to identify and track a specific cat, backed by a Model Context Protocol (MCP) server so Claude Desktop can answer natural-language queries ("Did Mimi go out today?"). The system runs on a Pi 5 with an optional Coral USB Accelerator for fast ML inference.

See [ROADMAP.md](ROADMAP.md) for the full 8-phase development plan.

## Target Hardware

- Raspberry Pi 5 (4GB/8GB) running Raspberry Pi OS 64-bit (Bookworm)
- Pi Camera Module 3 (CSI) or USB webcam (OpenCV path)
- Coral USB Accelerator (optional but strongly recommended for inference speed)

## Planned Architecture

```
Pi 5
├── capture/          # Camera ingestion (picamera2 or opencv)
├── detection/        # Motion detection (frame-diff) + YOLO object detection
├── classifier/       # Fine-tuned cat-identity model (fastai / HuggingFace)
├── storage/          # SQLite persistence for detections, snapshots, metadata
├── mcp_server/       # Python MCP server (SSE) exposing tools to Claude Desktop
└── dashboard/        # Optional Flask web UI (Phase 8)
```

### Key Data Flow

1. `capture/` grabs frames continuously; frame-differencing triggers on motion.
2. Motion frames go to `detection/` — YOLOv8n classifies species (cat / dog / person / other).
3. Cat frames go to `classifier/` — fine-tuned model identifies *which* cat.
4. Results + snapshots written to SQLite via `storage/`.
5. `mcp_server/` exposes MCP tools (`get_recent_detections`, `get_snapshot`, `get_cat_status`, `get_stats`) over SSE on the Pi's local IP.
6. Claude Desktop on the laptop connects to the MCP server for natural-language queries.

### MCP Server Tools (Phase 6+)

| Tool | Description |
|------|-------------|
| `get_recent_detections` | Latest N detection events with timestamps |
| `get_snapshot` | Return a specific image by detection ID |
| `get_cat_status` | Current inside/outside status based on last seen |
| `get_stats` | Aggregate stats over a time range |

## Development Workflow

Training (Phase 5) happens on a **laptop or Google Colab** (free GPU), not on the Pi. The resulting model file is then copied to the Pi via `scp`.

Inference and the MCP server run **on the Pi**. Connect via SSH for all Pi-side development.

## Key Dependencies (planned)

| Package | Purpose |
|---------|---------|
| `picamera2` | CSI camera capture on Pi |
| `opencv-python` | USB webcam capture + frame-differencing |
| `ultralytics` | YOLOv8n object detection |
| `fastai` or `transformers` | Fine-tuning cat identity classifier |
| `mcp` | Python MCP SDK for the SSE server |
| `sqlite3` | Built-in Python; persistence layer |
| `flask` | Optional Phase 8 web dashboard |
