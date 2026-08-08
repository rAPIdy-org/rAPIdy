import pytest
from rapidy_client._clock import Clock, SystemClock


def test_systemclock_satisfies_clock_protocol() -> None:
    assert isinstance(SystemClock(), Clock)


def test_systemclock_monotonic_nondecreasing() -> None:
    clock = SystemClock()
    assert clock.monotonic() <= clock.monotonic()


@pytest.mark.asyncio
async def test_systemclock_sleep_awaits() -> None:
    assert await SystemClock().sleep(0.0) is None
