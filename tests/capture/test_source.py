"""
Tests for capture/source.py

Hardware is never required to run these tests. cv2.VideoCapture and
picamera2 are replaced with mock objects so the tests run identically
on Windows, Mac, Linux, and CI.

Test organisation:
  - Error tests  : every RuntimeError / ValueError the module raises
  - Edge cases   : boundary conditions and defensive-coding paths
  - Behaviour    : looping, warm-up polling, context manager cleanup
"""

import sys
import time
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from capture.source import PiCameraSource, SourceController, VideoFileSource, WebcamSource

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_FRAME = np.zeros((720, 1280, 3), dtype=np.uint8)


def make_mock_cap(opened: bool = True, read_results=None):
    """Return a mock cv2.VideoCapture.

    read_results: list of (bool, frame) tuples returned by successive .read()
                  calls. Defaults to always returning a valid frame.
    """
    cap = MagicMock()
    cap.isOpened.return_value = opened
    if read_results is not None:
        cap.read.side_effect = read_results
    else:
        cap.read.return_value = (True, FAKE_FRAME)
    return cap


# ---------------------------------------------------------------------------
# Error tests — every exception the module can raise
# ---------------------------------------------------------------------------


class TestVideoFileSourceErrors:
    def test_raises_value_error_on_empty_paths(self):
        """Constructor must reject an empty path list immediately."""
        with pytest.raises(ValueError, match="at least one file path"):
            VideoFileSource(paths=[])

    def test_raises_runtime_error_when_file_cannot_be_opened(self):
        """start() must raise if cv2 cannot open the given path."""
        with patch("cv2.VideoCapture") as mock_cls:
            mock_cls.return_value = make_mock_cap(opened=False)
            source = VideoFileSource(paths=["does_not_exist.mp4"])
            with pytest.raises(RuntimeError, match="Could not open video file"):
                source.start()


class TestWebcamSourceErrors:
    def test_raises_runtime_error_when_device_not_found(self):
        """start() must raise if the requested camera index is unavailable."""
        with patch("cv2.VideoCapture") as mock_cls:
            mock_cls.return_value = make_mock_cap(opened=False)
            source = WebcamSource(device_index=99)
            with pytest.raises(RuntimeError, match="Could not open webcam"):
                source.start()


class TestPiCameraSourceErrors:
    def test_raises_runtime_error_when_picamera2_not_installed(self):
        """start() must raise a clear message when not running on a Pi."""
        with patch.dict(sys.modules, {"picamera2": None}):
            source = PiCameraSource()
            with pytest.raises(RuntimeError, match="picamera2 is not available"):
                source.start()


# ---------------------------------------------------------------------------
# Edge cases — defensive paths and boundary conditions
# ---------------------------------------------------------------------------


class TestReadFrameBeforeStart:
    """Calling read_frame() before start() must never crash — return (False, None)."""

    def test_video_file_source(self):
        source = VideoFileSource(paths=["any.mp4"])
        success, frame = source.read_frame()
        assert success is False
        assert frame is None

    def test_webcam_source(self):
        source = WebcamSource()
        success, frame = source.read_frame()
        assert success is False
        assert frame is None

    def test_picamera_source(self):
        source = PiCameraSource()
        success, frame = source.read_frame()
        assert success is False
        assert frame is None


class TestStopIdempotency:
    """Calling stop() more than once must be a safe no-op."""

    def test_webcam_stop_twice(self):
        with patch("cv2.VideoCapture") as mock_cls:
            mock_cls.return_value = make_mock_cap()
            source = WebcamSource()
            source.start()
            source.stop()
            source.stop()  # must not raise

    def test_picamera_stop_twice(self):
        mock_pi = MagicMock()
        mock_camera = MagicMock()
        mock_pi.Picamera2.return_value = mock_camera
        with patch.dict(sys.modules, {"picamera2": mock_pi}):
            source = PiCameraSource()
            source.start()
            source.stop()
            source.stop()  # must not raise

    def test_video_file_stop_twice(self):
        with patch("cv2.VideoCapture") as mock_cls:
            mock_cls.return_value = make_mock_cap()
            source = VideoFileSource(paths=["clip.mp4"])
            source.start()
            source.stop()
            source.stop()  # must not raise


class TestPiCameraReadFrameHandlesSensorException:
    """A mid-stream sensor error must return (False, None), not propagate an exception."""

    def test_capture_array_exception_is_caught(self):
        mock_pi = MagicMock()
        mock_camera = MagicMock()
        mock_camera.capture_array.side_effect = Exception("sensor overheated")
        mock_pi.Picamera2.return_value = mock_camera
        with patch.dict(sys.modules, {"picamera2": mock_pi}):
            source = PiCameraSource()
            source.start()
            success, frame = source.read_frame()
            assert success is False
            assert frame is None


# ---------------------------------------------------------------------------
# Behaviour tests — looping, warm-up, context manager
# ---------------------------------------------------------------------------


class TestVideoFileSourceLooping:
    def test_single_file_loops_when_loop_true(self):
        """After the file ends, read_frame() must continue delivering frames."""
        # read() fails on the 3rd call (end-of-file), succeeds otherwise
        results = [(True, FAKE_FRAME), (True, FAKE_FRAME), (False, None), (True, FAKE_FRAME)]
        with patch("cv2.VideoCapture") as mock_cls:
            mock_cls.return_value = make_mock_cap(read_results=results)
            source = VideoFileSource(paths=["mimi.mp4"], loop=True)
            source.start()

            assert source.read_frame() == (True, FAKE_FRAME)
            assert source.read_frame() == (True, FAKE_FRAME)
            # File ends here — _advance() re-opens the same file and reads again
            success, frame = source.read_frame()
            assert success is True

    def test_single_file_exhausts_when_loop_false(self):
        """With loop=False the source must return (False, None) once the file ends."""
        results = [(True, FAKE_FRAME), (False, None), (False, None)]
        with patch("cv2.VideoCapture") as mock_cls:
            mock_cls.return_value = make_mock_cap(read_results=results)
            source = VideoFileSource(paths=["mimi.mp4"], loop=False)
            source.start()

            assert source.read_frame()[0] is True
            success, frame = source.read_frame()
            assert success is False
            assert frame is None

    def test_multiple_files_played_in_order(self):
        """With multiple paths the source must open each file in sequence."""
        with patch("cv2.VideoCapture") as mock_cls:
            mock_cls.return_value = make_mock_cap(
                read_results=[(True, FAKE_FRAME), (False, None), (True, FAKE_FRAME)]
            )
            source = VideoFileSource(
                paths=["mimi_morning.mp4", "mimi_door.mp4"],
                loop=False,
            )
            source.start()

            source.read_frame()  # from first file
            source.read_frame()  # triggers advance to second file
            # cv2.VideoCapture should have been constructed twice
            assert mock_cls.call_count == 2


class TestWaitForReady:
    def test_returns_true_on_first_successful_frame(self):
        with patch("cv2.VideoCapture") as mock_cls:
            mock_cls.return_value = make_mock_cap()
            source = WebcamSource()
            source.start()
            with patch("time.sleep"):
                assert source.wait_for_ready(timeout_s=5.0) is True

    def test_returns_false_when_camera_never_delivers_frame(self):
        with patch("cv2.VideoCapture") as mock_cls:
            mock_cls.return_value = make_mock_cap(read_results=[(False, None)] * 100)
            source = WebcamSource()
            source.start()
            # Use a real short timeout so the clock actually expires
            with patch("time.sleep"):
                result = source.wait_for_ready(timeout_s=0.05, poll_interval_s=0.01)
            assert result is False

    def test_returns_true_after_several_failures(self):
        """Simulates camera warm-up: first 3 reads are black, then it's ready."""
        results = [(False, None), (False, None), (False, None), (True, FAKE_FRAME)]
        with patch("cv2.VideoCapture") as mock_cls:
            mock_cls.return_value = make_mock_cap(read_results=results)
            source = WebcamSource()
            source.start()
            with patch("time.sleep"):
                assert source.wait_for_ready(timeout_s=10.0) is True


class TestContextManager:
    def test_stop_is_called_on_normal_exit(self):
        with patch("cv2.VideoCapture") as mock_cls:
            cap = make_mock_cap()
            mock_cls.return_value = cap
            source = WebcamSource()
            with source:
                pass
            cap.release.assert_called_once()

    def test_stop_is_called_even_when_exception_raised(self):
        """The context manager must release hardware even if the body throws."""
        with patch("cv2.VideoCapture") as mock_cls:
            cap = make_mock_cap()
            mock_cls.return_value = cap
            source = WebcamSource()
            with pytest.raises(ValueError):
                with source:
                    raise ValueError("something went wrong in the pipeline")
            cap.release.assert_called_once()
