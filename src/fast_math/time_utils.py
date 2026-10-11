# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
import dataclasses
import datetime as dt
import time
from typing import Any, final, Literal, overload


@final
@dataclasses.dataclass(frozen=True, slots=True, order=True, kw_only=True)
class TimePoint:
    """Analogous to `datetime.datetime`, but using the clock from
`time.monotonic_ns` (and thus not aligned to any wall clock or system clock).
Still supports addition and subtraction with itself and `datetime.timedelta`
similar to `datetime.datetime`. `now()` static method gets value from
`time.monotonic_ns`. Has microsecond precision, just like `datetime.datetime`,
so as to not introduce rounding errors with math operations."""
    microseconds: int

    def __post_init__(self, /) -> None:
        if not isinstance(self.microseconds, int):  # type: ignore
            raise TypeError("timestamp_us must be an int")

    @staticmethod
    def now() -> TimePoint:
        return TimePoint(microseconds=(time.monotonic_ns() + 500) // 1000)

    def __add__(self, other: dt.timedelta, /) -> TimePoint:
        if not isinstance(other, dt.timedelta):  # type: ignore
            return NotImplemented
        other_us: int = other // dt.timedelta(microseconds=1)
        return TimePoint(microseconds=self.microseconds + other_us)

    __radd__ = __add__

    @overload
    def __sub__(self, other: dt.timedelta, /) -> TimePoint:
        ...

    @overload
    def __sub__(self, other: TimePoint, /) -> dt.timedelta:
        ...

    def __sub__(self, other: Any, /) -> Any:
        match other:
            case TimePoint():
                return dt.timedelta(
                    microseconds=self.microseconds - other.microseconds
                )
            case dt.timedelta():
                other_us: int = other // dt.timedelta(microseconds=1)
                return TimePoint(microseconds=self.microseconds - other_us)
            case _:
                return NotImplemented


@final
class Stopwatch:
    """Generalized domain object, non-negative time not guaranteed. To use,
construct with a function that returns the current time. You can then:
* Get/set `elapsed`
    * Samples current time once iff `running`
* Get/set `started_at`
    * Samples current time once iff not `running`
* Get/set `running`
    * Get does not sample current time
    * Set samples current time if changed to different value"""
    __slots__ = ("_now", "_elapsed_or_started_at")

    _now: Callable[[], TimePoint]
    _elapsed_or_started_at: dt.timedelta | TimePoint

    def __init__(self, now: Callable[[], TimePoint], /) -> None:
        self._now = now
        self._elapsed_or_started_at = dt.timedelta()

    @staticmethod
    def started_now(now: Callable[[], TimePoint], /) -> Stopwatch:
        result = Stopwatch(now)
        result.running = True
        return result

    @property
    def elapsed(self, /) -> dt.timedelta:
        match self._elapsed_or_started_at:
            case dt.timedelta() as elapsed:
                return elapsed
            case TimePoint() as started_at:
                return self._now() - started_at

    @elapsed.setter
    def elapsed(self, to: dt.timedelta, /) -> None:
        match self._elapsed_or_started_at:
            case dt.timedelta():
                self._elapsed_or_started_at = to
            case TimePoint():
                self._elapsed_or_started_at = self._now() - to

    @property
    def started_at(self, /) -> TimePoint:
        match self._elapsed_or_started_at:
            case dt.timedelta() as elapsed:
                return self._now() - elapsed
            case TimePoint() as started_at:
                return started_at

    @started_at.setter
    def started_at(self, to: TimePoint, /) -> None:
        match self._elapsed_or_started_at:
            case dt.timedelta():
                self._elapsed_or_started_at = self._now() - to
            case TimePoint():
                self._elapsed_or_started_at = to

    @property
    def running(self, /) -> bool:
        return isinstance(self._elapsed_or_started_at, TimePoint)

    @running.setter
    def running(self, to: bool, /) -> None:
        if self.running == to:
            return
        self._elapsed_or_started_at = self._now() - self._elapsed_or_started_at


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ImmutableStopwatch:
    """Like `Stopwatch`, but cannot be paused, and nothing can be changed."""
    now: Callable[[], TimePoint]
    started_at: TimePoint

    @staticmethod
    def started_now(now: Callable[[], TimePoint], /) -> ImmutableStopwatch:
        return ImmutableStopwatch(now, now())

    @property
    def elapsed(self, /) -> dt.timedelta:
        return self.now() - self.started_at

    @property
    def running(self, /) -> Literal[True]:
        return True


@final
class Timer:
    """Generalized domain object, non-negative time not guaranteed. To use,
construct with a function that returns the current time. You can then:
* Get/set `remaining`
    * Samples current time once iff `running`
* Get/set `deadline`
    * Samples current time once iff not `running`
* Get/set `running`
    * Get does not sample current time
    * Set samples current time if changed to different value"""
    __slots__ = ("_stopwatch", "_finish_at")

    _stopwatch: Stopwatch
    _finish_at: dt.timedelta

    def __init__(self, now: Callable[[], TimePoint], /) -> None:
        self._stopwatch = Stopwatch(now)
        self._finish_at = dt.timedelta()

    @property
    def remaining(self, /) -> dt.timedelta:
        return self._finish_at - self._stopwatch.elapsed

    @remaining.setter
    def remaining(self, to: dt.timedelta, /) -> None:
        self._finish_at = self._stopwatch.elapsed + to

    @property
    def deadline(self, /) -> TimePoint:
        return self._stopwatch.started_at + self._finish_at

    @deadline.setter
    def deadline(self, to: TimePoint, /) -> None:
        self._finish_at = to - self._stopwatch.started_at

    @property
    def running(self, /) -> bool:
        return self._stopwatch.running

    @running.setter
    def running(self, to: bool, /) -> None:
        self._stopwatch.running = to


def seconds_string(td: dt.timedelta, /) -> str:
    sign: str = "-" if td < dt.timedelta() else ""
    td = abs(td)
    minutes, seconds = divmod(td.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    hours += td.days * 24
    if hours > 0:
        return f"{sign}{hours}:{minutes:02}:{seconds:02}"
    return f"{sign}{minutes}:{seconds:02}"
