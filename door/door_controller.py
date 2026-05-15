"""
Door controller abstraction and implementations.

Three implementations share a common interface (DoorController) and inherit
shared timeout/state logic from _BaseDoorController:

  ConsoleDoorController  — logs state changes; runs on any OS, no hardware needed
  LEDDoorController      — red/green GPIO LEDs on Raspberry Pi (gpiozero, lazy import)
  ServoDoorController    — servo motor placeholder for a real latch (Phase 9+)

Usage:
    controller = ConsoleDoorController()
    controller.start()
    controller.unlock(timeout_seconds=30)
    print(controller.get_status())   # {"state": "unlocked", "seconds_remaining": 28}
    controller.lock()
    controller.stop()
"""

from __future__ import annotations

import abc
import logging
import threading
import time

logger = logging.getLogger(__name__)


class DoorController(abc.ABC):
    """Public interface every door controller must satisfy."""

    def start(self) -> None:
        """Initialize hardware (GPIO, servo). Default is a no-op."""

    @abc.abstractmethod
    def lock(self) -> None:
        """Lock the door immediately, cancelling any active auto-lock timer."""

    @abc.abstractmethod
    def unlock(self, timeout_seconds: int = 30) -> None:
        """Unlock the door and automatically re-lock after timeout_seconds."""

    @abc.abstractmethod
    def get_status(self) -> dict:
        """Return current state.

        Returns:
            {"state": "locked" | "unlocked", "seconds_remaining": int | None}
            seconds_remaining is None when locked, otherwise the time left
            before auto-lock fires.
        """

    def stop(self) -> None:
        """Release hardware resources. Default is a no-op."""


class _BaseDoorController(DoorController):
    """Shared timeout and state management.

    Subclasses implement _on_lock() and _on_unlock() for their physical
    output (LEDs, servo, log line, etc.). Everything else lives here once.
    """

    def __init__(self) -> None:
        self._locked = True
        self._unlock_time: float | None = None
        self._timeout_seconds: int | None = None
        self._timer: threading.Timer | None = None

    @abc.abstractmethod
    def _on_lock(self) -> None:
        """Trigger the physical locked output."""

    @abc.abstractmethod
    def _on_unlock(self) -> None:
        """Trigger the physical unlocked output."""

    def lock(self) -> None:
        self._cancel_timer()
        self._locked = True
        self._unlock_time = None
        self._timeout_seconds = None
        self._on_lock()

    def unlock(self, timeout_seconds: int = 30) -> None:
        self._cancel_timer()
        self._locked = False
        self._unlock_time = time.monotonic()
        self._timeout_seconds = timeout_seconds
        self._on_unlock()
        self._timer = threading.Timer(timeout_seconds, self._on_timeout)
        self._timer.daemon = True
        self._timer.start()

    def _on_timeout(self) -> None:
        self._locked = True
        self._unlock_time = None
        self._timeout_seconds = None
        self._on_lock()
        logger.info("[DOOR] Auto-locked after timeout")

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def get_status(self) -> dict:
        if self._locked:
            return {"state": "locked", "seconds_remaining": None}
        elapsed = time.monotonic() - self._unlock_time  # type: ignore[operator]
        remaining = max(0, self._timeout_seconds - int(elapsed))  # type: ignore[operator]
        return {"state": "unlocked", "seconds_remaining": remaining}


class ConsoleDoorController(_BaseDoorController):
    """Development implementation — no hardware required.

    Logs every state change to the console so you can verify the full
    pipeline logic on Mac/Windows before any Pi wiring is done.
    """

    def _on_lock(self) -> None:
        logger.info("[DOOR] LOCKED")
        print("[DOOR] LOCKED")

    def _on_unlock(self) -> None:
        logger.info("[DOOR] UNLOCKED (auto-lock in %ds)", self._timeout_seconds)
        print(f"[DOOR] UNLOCKED (auto-lock in {self._timeout_seconds}s)")


class LEDDoorController(_BaseDoorController):
    """Red/green LED implementation — Raspberry Pi only.

    gpiozero is imported lazily inside start() so this file can be imported
    on Mac/Windows without raising ImportError.

    Wiring:
        green_pin (default GPIO 27) — green LED anode via 330Ω resistor to GND
        red_pin   (default GPIO 17) — red LED anode via 330Ω resistor to GND
    """

    def __init__(self, green_pin: int = 27, red_pin: int = 17) -> None:
        super().__init__()
        self._green_pin = green_pin
        self._red_pin = red_pin
        self._green = None
        self._red = None

    def start(self) -> None:
        try:
            from gpiozero import LED
        except ImportError as exc:
            raise RuntimeError(
                "gpiozero is not available. LEDDoorController only runs on Raspberry Pi."
            ) from exc
        self._green = LED(self._green_pin)
        self._red = LED(self._red_pin)
        self._on_lock()
        logger.info("LEDDoorController started (green=GPIO%d, red=GPIO%d)", self._green_pin, self._red_pin)

    def _on_lock(self) -> None:
        if self._red:
            self._red.on()
        if self._green:
            self._green.off()
        logger.info("[DOOR] RED LED — LOCKED")

    def _on_unlock(self) -> None:
        if self._red:
            self._red.off()
        if self._green:
            self._green.on()
        logger.info("[DOOR] GREEN LED — UNLOCKED (auto-lock in %ds)", self._timeout_seconds)

    def stop(self) -> None:
        self._cancel_timer()
        if self._red:
            self._red.close()
        if self._green:
            self._green.close()
        self._red = None
        self._green = None
        logger.info("LEDDoorController stopped")


class ServoDoorController(_BaseDoorController):
    """Servo motor implementation — Raspberry Pi only, Phase 9+ extension.

    Physical latch control via PWM servo. Not yet implemented — requires
    hardware wiring and per-servo angle calibration before the locked/unlocked
    positions can be set. Raises NotImplementedError until then.
    """

    def __init__(self, servo_pin: int = 18) -> None:
        super().__init__()
        self._servo_pin = servo_pin

    def _on_lock(self) -> None:
        raise NotImplementedError(
            "ServoDoorController is a Phase 9 placeholder. "
            "Wire and calibrate the servo before implementing."
        )

    def _on_unlock(self) -> None:
        raise NotImplementedError(
            "ServoDoorController is a Phase 9 placeholder. "
            "Wire and calibrate the servo before implementing."
        )
