import pytest

from app.game.host_pin import HostPinGuard, resolve_host_pin

PIN = 'rehearsal-pin-1234'


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_default_pin_is_long_and_random() -> None:
    first, second = resolve_host_pin(None), resolve_host_pin(None)
    assert len(first) >= 8
    assert first != second


def test_configured_pin_must_be_at_least_eight_characters() -> None:
    assert resolve_host_pin(PIN) == PIN
    with pytest.raises(ValueError, match='at least 8 characters'):
        resolve_host_pin('1234')


def test_non_ascii_pin_is_rejected_without_raising() -> None:
    assert HostPinGuard(PIN, FakeClock()).accepts('ü-not-ascii') is False


def test_lockout_after_ten_bad_pins_then_recovers() -> None:
    clock = FakeClock()
    guard = HostPinGuard(PIN, clock)
    for _ in range(10):
        assert guard.accepts('wrong') is False
    assert guard.accepts(PIN) is False
    clock.now += 61
    assert guard.accepts(PIN) is True
