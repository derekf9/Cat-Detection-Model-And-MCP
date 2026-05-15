# Phase 2 — Camera Capture and Motion Detection

## Goal
Build the capture pipeline with a `SourceController` abstraction so the same code runs on
the Pi (real camera), Mac/Windows (webcam or video file), and in tests (Mochi recordings).

## Status
- [ ] In progress

## Key Design Decision: SourceController

The capture loop never imports hardware libraries directly.
It only calls `source.read_frame()` — the source object hides the details.

```
capture/
├── source.py            # SourceController base + PiCameraSource, WebcamSource, VideoFileSource
└── capture_motion.py    # Motion loop — only talks to a SourceController
```

### How to run on each platform

| Platform | Command |
|----------|---------|
| Pi (real camera) | `python -m capture.capture_motion --source pi` |
| Mac/Windows (webcam) | `python -m capture.capture_motion --source webcam` |
| Mac/Windows (test video) | `python -m capture.capture_motion --source file --path data/test/mochi_morning.mp4` |

## Test Video Plan
Record on Pi, use everywhere else:
- `data/test/mochi_morning.mp4` — indoor, morning light
- `data/test/mochi_door.mp4` — near the door (key for inside/outside logic)
- `data/test/mochi_evening.mp4` — lower light conditions
- `data/test/mochi_still.mp4` — Mochi sitting still (motion threshold tuning)

`data/test/` is gitignored — videos live locally or shared via Google Drive.

## Done When
- [ ] `SourceController`, `PiCameraSource`, `WebcamSource`, `VideoFileSource` implemented
- [ ] `--source` CLI flag wired up
- [ ] Motion detection loop saves snapshots to `data/snapshots/YYYY-MM-DD/`
- [ ] Runs on Pi with real camera
- [ ] Runs on Mac/Windows with a test video file
- [ ] 3+ Mochi test videos recorded and stored locally
