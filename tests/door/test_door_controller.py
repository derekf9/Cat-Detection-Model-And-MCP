"""
Tests for door/door_controller.py

No hardware is required. threading.Timer is mocked so timeout behaviour
can be verified instantly without real sleeps.
"""

import sys
import threading
from unittest.mock import MagicMock, call, patch

import pytest

from door.door_controller import (
    ConsoleDoorController,
    DoorController,
    LEDDoorController,
    ServoDoorController,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_led_controller(green_pin: int = 27, red_pin: int = 17) -> tuple[LEDDoorController, MagicMock, MagicMock]:
    """Return a started LEDDoorController with mocked GPIO LED objects."""
    mock_green = MagicMock()
    mock_red = MagicMock()

    mock_gpiozero = MagicMock()
    # LED(pin) returns green or red mock depending on which pin was passed
    mock_gpiozero.LED.side_effect = lambda pin: mock_green if pin == green_pin else mock_red

    with patch.dict(sys.modules, {"gpiozero": mock_gpiozero}):
        controller = LEDDoorController(green_pin=green_pin, red_pin=red_pin)
        controller.start()

    return controller, mock_green, mock_red


# ---------------------------------------------------------------------------
# Error tests
# ---------------------------------------------------------------------------


class TestLEDDoorControllerErrors:
    def test_raises_when_gpiozero_not_installed(self):
        with patch.dict(sys.modules, {"gpiozero": None}):
            controller = LEDDoorController()
            with pytest.raises(RuntimeError, match="gpiozero is not available"):
                controller.start()


class TestServoDoorControllerErrors:
    def test_lock_raises_not_implemented(self):
        controller = ServoDoorController()
        with pytest.raises(NotImplementedError):
            controller.lock()

    def test_unlock_raises_not_implemented(self):
        controller = ServoDoorController()
        with pytest.raises(NotImplementedError):
            controller.unlock()

    def test_get_status_raises_not_implemented(self):
        """get_status() on a ServoDoorController should raise once lock() or
        unlock() is called, since _on_lock/_on_unlock are not implemented."""
        controller = ServoDoorController()
        with pytest.raises(NotImplementedError):
            controller.lock()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestInitialState:
    """Every controller must start in the locked state."""

    def test_console_starts_locked(self):
        controller = ConsoleDoorController()
        assert controller.get_status()["state"] == "locked"

    def test_led_starts_locked_and_sets_red_on(self):
        controller, mock_green, mock_red = make_led_controller()
        assert controller.get_status()["state"] == "locked"
        mock_red.on.assert_called()
        mock_green.off.assert_called()


class TestLockWhenAlreadyLocked:
    """Calling lock() on an already-locked controller must not raise."""

    def test_console_lock_idempotent(self):
        controller = ConsoleDoorController()
        controller.lock()
        controller.lock()  # must not raise
        assert controller.get_status()["state"] == "locked"


class TestUnlockResetsTimer:
    """Calling unlock() while already unlocked must restart the timeout."""

    def test_console_unlock_twice_resets_timer(self):
        with patch("door.door_controller.threading.Timer") as mock_timer_cls:
            mock_timer = MagicMock()
            mock_timer_cls.return_value = mock_timer

            controller = ConsoleDoorController()
            controller.unlock(timeout_seconds=30)
            controller.unlock(timeout_seconds=60)

            # First timer must have been cancelled before second was started
            mock_timer.cancel.assert_called_once()
            assert mock_timer_cls.call_count == 2


class TestStopIdempotency:
    """Calling stop() more than once must be safe."""

    def test_led_stop_twice(self):
        controller, mock_green, mock_red = make_led_controller()
        controller.stop()
        controller.stop()  # must not raise


# ---------------------------------------------------------------------------
# Behaviour tests
# ---------------------------------------------------------------------------


class TestLockCancelsActiveTimer:
    def test_manual_lock_cancels_pending_timeout(self):
        with patch("door.door_controller.threading.Timer") as mock_timer_cls:
            mock_timer = MagicMock()
            mock_timer_cls.return_value = mock_timer

            controller = ConsoleDoorController()
            controller.unlock(timeout_seconds=30)
            controller.lock()

            mock_timer.cancel.assert_called_once()
            assert controller.get_status()["state"] == "locked"
            assert controller.get_status()["seconds_remaining"] is None


class TestTimeoutAutoLock:
    def test_timeout_callback_sets_state_to_locked(self):
        """Simulate the timer firing by calling _on_timeout directly."""
        controller = ConsoleDoorController()
        controller.unlock(timeout_seconds=30)
        assert controller.get_status()["state"] == "unlocked"

        controller._on_timeout()

        assert controller.get_status()["state"] == "locked"
        assert controller.get_status()["seconds_remaining"] is None


class TestGetStatusSecondsRemaining:
    def test_locked_returns_none_for_seconds_remaining(self):
        controller = ConsoleDoorController()
        status = controller.get_status()
        assert status["state"] == "locked"
        assert status["seconds_remaining"] is None

    def test_unlocked_returns_positive_seconds_remaining(self):
        with patch("door.door_controller.threading.Timer"):
            controller = ConsoleDoorController()
            controller.unlock(timeout_seconds=60)
            status = controller.get_status()
            assert status["state"] == "unlocked"
            assert 0 < status["seconds_remaining"] <= 60


class TestLEDOutputSignals:
    def test_unlock_turns_green_on_and_red_off(self):
        controller, mock_green, mock_red = make_led_controller()
        with patch("door.door_controller.threading.Timer"):
            controller.unlock(timeout_seconds=30)
        mock_green.on.assert_called()
        mock_red.off.assert_called()

    def test_lock_turns_red_on_and_green_off(self):
        controller, mock_green, mock_red = make_led_controller()
        with patch("door.door_controller.threading.Timer"):
            controller.unlock(timeout_seconds=30)
            mock_green.reset_mock()
            mock_red.reset_mock()
            controller.lock()
        mock_red.on.assert_called()
        mock_green.off.assert_called()

    def test_stop_closes_both_leds(self):
        controller, mock_green, mock_red = make_led_controller()
        controller.stop()
        mock_green.close.assert_called_once()
        mock_red.close.assert_called_once()
