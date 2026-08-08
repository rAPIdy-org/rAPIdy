import asyncio

import pytest
from rapidy_client._clock import Clock, SystemClock
from rapidy_client.testing import FakeClock


def test_systemclock_satisfies_clock_protocol() -> None:
    assert isinstance(SystemClock(), Clock)


def test_systemclock_monotonic_nondecreasing() -> None:
    clock = SystemClock()
    assert clock.monotonic() <= clock.monotonic()


@pytest.mark.asyncio
async def test_systemclock_sleep_awaits() -> None:
    assert await SystemClock().sleep(0.0) is None


def test_fake_clock_satisfies_clock_protocol() -> None:
    assert isinstance(FakeClock(), Clock)


def test_fake_clock_monotonic_starts_at_configured_value() -> None:
    assert FakeClock().monotonic() == 0.0
    assert FakeClock(start=5.0).monotonic() == 5.0


@pytest.mark.asyncio
async def test_fake_clock_sleep_advances_virtual_time() -> None:
    clock = FakeClock()

    await clock.sleep(3.0)
    await clock.sleep(1.5)

    assert clock.monotonic() == 4.5


@pytest.mark.asyncio
async def test_fake_clock_sleep_has_no_real_wait() -> None:
    clock = FakeClock()

    async with asyncio.timeout(0.5):
        for _ in range(100):
            await clock.sleep(10.0)

    assert clock.monotonic() == 1000.0


@pytest.mark.asyncio
async def test_fake_clock_negative_delay_does_not_move_backward() -> None:
    clock = FakeClock(start=2.0)

    await clock.sleep(-1.0)

    assert clock.monotonic() == 2.0


@pytest.mark.asyncio
async def test_fake_clock_monotonic_is_nondecreasing() -> None:
    clock = FakeClock()
    previous = clock.monotonic()

    for _ in range(10):
        await clock.sleep(0.1)
        current = clock.monotonic()
        assert current >= previous
        previous = current
