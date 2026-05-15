from __future__ import annotations

import abc
import logging
import time
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class SourceController(abc.ABC):
    """Contract that all video sources must satisfy.

    The capture loop and detection pipeline only ever call read_frame() —
    they are completely unaware of what hardware or file sits underneath.

    Usage pattern:
        with WebcamSource() as source:
            if not source.wait_for_ready():
                raise RuntimeError("Camera failed to initialize")
            while True:
                success, frame = source.read_frame()
                ...
    """

    def start(self) -> None:
        """Open the device or file and prepare to deliver frames."""

    @abc.abstractmethod
    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        """Return (success, frame).

        frame is a BGR uint8 ndarray of shape (H, W, 3), or None on failure.
        This matches the return type of cv2.VideoCapture.read() so the rest
        of the pipeline can treat all sources identically.
        """

    def stop(self) -> None:
        """Release all hardware handles and file descriptors."""

    def wait_for_ready(
        self,
        timeout_s: float = 10.0,
        poll_interval_s: float = 0.5,
    ) -> bool:
        """Block until the source delivers a valid frame or timeout elapses.

        Cameras (both Pi CSI and USB webcam) need a warm-up period — the
        first frames are often black or corrupt while the sensor auto-adjusts.
        Polling here drains those bad frames before the pipeline starts.

        Returns True if ready, False if timed out.
        """
        deadline = time.monotonic() + timeout_s
        attempts = 0
        while time.monotonic() < deadline:
            success, _ = self.read_frame()
            if success:
                logger.debug("%s ready after %d poll(s)", self.__class__.__name__, attempts + 1)
                return True
            attempts += 1
            logger.debug(
                "%s not ready (attempt %d), retrying in %.1fs",
                self.__class__.__name__,
                attempts,
                poll_interval_s,
            )
            time.sleep(poll_interval_s)

        logger.error(
            "%s failed to become ready within %.1fs (%d attempts)",
            self.__class__.__name__,
            timeout_s,
            attempts,
        )
        return False

    def __enter__(self) -> SourceController:
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()


class PiCameraSource(SourceController):
    """CSI camera via picamera2 — Raspberry Pi only.

    picamera2 is imported lazily inside start() so this file can be imported
    on Mac/Windows without raising ImportError. Attempting to call start() on
    a non-Pi machine will raise a clear RuntimeError.
    """

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        self._width = width
        self._height = height
        self._camera = None

    def start(self) -> None:
        try:
            from picamera2 import Picamera2
        except ImportError as exc:
            raise RuntimeError(
                "picamera2 is not available. PiCameraSource only runs on Raspberry Pi."
            ) from exc

        self._camera = Picamera2()
        config = self._camera.create_preview_configuration(
            main={"size": (self._width, self._height), "format": "BGR888"}
        )
        self._camera.configure(config)
        self._camera.start()
        logger.info("PiCameraSource started (%dx%d)", self._width, self._height)

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if self._camera is None:
            return False, None
        try:
            frame = self._camera.capture_array()
            return True, frame
        except Exception as exc:
            logger.warning("PiCameraSource read error: %s", exc)
            return False, None

    def stop(self) -> None:
        if self._camera is not None:
            self._camera.stop()
            self._camera.close()
            self._camera = None
            logger.info("PiCameraSource stopped")


class WebcamSource(SourceController):
    """USB webcam or built-in laptop camera via OpenCV."""

    def __init__(self, device_index: int = 0, width: int = 1280, height: int = 720) -> None:
        self._device_index = device_index
        self._width = width
        self._height = height
        self._cap: cv2.VideoCapture | None = None

    def start(self) -> None:
        self._cap = cv2.VideoCapture(self._device_index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Could not open webcam at device index {self._device_index}. "
                "Is a camera plugged in?"
            )
        logger.info(
            "WebcamSource started (device %d, %dx%d)",
            self._device_index,
            self._width,
            self._height,
        )

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if self._cap is None or not self._cap.isOpened():
            return False, None
        success, frame = self._cap.read()
        if not success:
            logger.warning("WebcamSource: failed to read frame")
            return False, None
        return True, frame

    def stop(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("WebcamSource stopped")


class VideoFileSource(SourceController):
    """One or more video files played back in sequence, with optional looping.

    Accepts a list of paths so you can queue multiple test clips of Mimi.
    When the last file ends and loop=True, playback restarts from the first
    file — simulating the continuous nature of a real camera stream.

    Example:
        source = VideoFileSource(
            paths=["data/test/mimi_morning.mp4", "data/test/mimi_door.mp4"],
            loop=True,
        )
    """

    def __init__(self, paths: list[str | Path], loop: bool = True) -> None:
        if not paths:
            raise ValueError("VideoFileSource requires at least one file path.")
        self._paths = [str(p) for p in paths]
        self._loop = loop
        self._index = 0
        self._cap: cv2.VideoCapture | None = None

    def start(self) -> None:
        self._index = 0
        self._open_current()

    def _open_current(self) -> None:
        if self._cap is not None:
            self._cap.release()
        path = self._paths[self._index]
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open video file: {path}")
        logger.info(
            "VideoFileSource opened [%d/%d]: %s",
            self._index + 1,
            len(self._paths),
            path,
        )

    def _advance(self) -> bool:
        """Step to the next file. Returns False when all files are exhausted and loop=False."""
        next_index = self._index + 1
        if next_index >= len(self._paths):
            if not self._loop:
                logger.info("VideoFileSource: all files exhausted (loop=False)")
                return False
            next_index = 0
            logger.debug("VideoFileSource: looping back to first file")
        self._index = next_index
        self._open_current()
        return True

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if self._cap is None:
            return False, None

        success, frame = self._cap.read()

        if not success:
            # Current file ended — try the next one
            if not self._advance():
                return False, None
            success, frame = self._cap.read()

        return (True, frame) if success else (False, None)

    def stop(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("VideoFileSource stopped")
