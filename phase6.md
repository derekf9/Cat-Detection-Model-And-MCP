# Phase 6 — Pet Door Control and Physical Feedback

## Goal
Wire a physical LED indicator to the Pi's GPIO pins and build door control logic.
When Mimi is detected approaching the door, the system auto-unlocks (green LED).
MCP tools allow Claude Desktop to manually lock/unlock with a timeout.
SQLite tracks all door events so ingress/egress patterns become queryable.

## Design: DoorController Abstraction

Mirrors the `SourceController` pattern — the pipeline never imports GPIO directly.

```
door/
├── door_controller.py   # DoorController base + all implementations
```

| Class | Runs on | Use for |
|-------|---------|---------|
| `ConsoleDoorController` | Any OS | Development and testing without hardware |
| `LEDDoorController` | Raspberry Pi | Red/green GPIO LEDs (gpiozero) |
| `ServoDoorController` | Raspberry Pi | Physical latch — Phase 9+ placeholder |

### How to run

```bash
# Development (any OS) — console logging only
python -m door.door_controller --controller console

# Pi with LEDs wired
python -m door.door_controller --controller led
```

## Hardware Wiring

```
Pi GPIO 27 → 330Ω resistor → Green LED anode → GND   (unlocked)
Pi GPIO 17 → 330Ω resistor → Red LED anode   → GND   (locked)
```

Default state on startup: **locked** (red LED on).

## Tasks

### Door Controller
- [x] `DoorController` abstract base class
- [x] `_BaseDoorController` — shared timeout/state logic
- [x] `ConsoleDoorController` — dev implementation
- [x] `LEDDoorController` — GPIO LEDs, lazy gpiozero import
- [x] `ServoDoorController` — placeholder, raises NotImplementedError
- [x] Unit tests in `tests/door/test_door_controller.py`

### Auto-Unlock Integration (depends on Phase 5 classifier)
- [ ] Define configurable "door zone" bounding box in a config file
- [ ] In the capture/detection pipeline: when Mimi's centroid enters the door zone → call `controller.unlock(timeout_seconds=30)`
- [ ] Log every auto-unlock event to SQLite `door_events` table

### SQLite Schema (add to Phase 8 storage module)
```sql
CREATE TABLE door_events (
  id            TEXT PRIMARY KEY,
  timestamp     TEXT NOT NULL,
  event_type    TEXT NOT NULL,  -- 'auto_unlock', 'manual_unlock', 'manual_lock', 'timeout_lock'
  triggered_by  TEXT,           -- 'mimi_detected', 'claude_desktop', 'timeout', 'startup'
  duration_s    INTEGER
);
```

### MCP Tools (add in Phase 7)
- [ ] `unlock_door(timeout_seconds: int = 30)`
- [ ] `lock_door()`
- [ ] `get_door_status()` → `{"state": "locked"|"unlocked", "seconds_remaining": int|None}`
- [ ] `get_door_patterns()` — peak times, average time outside, trips per day

## Done When
- [ ] Red LED on = locked, green LED on = unlocked — visible at a glance on the Pi
- [ ] Mimi approaching door zone auto-unlocks (green) and re-locks after timeout
- [ ] Claude Desktop can call `unlock_door(timeout_seconds=60)` and `lock_door()`
- [ ] All door events logged to SQLite
- [ ] `ConsoleDoorController` passes all tests on Mac/Windows without Pi
