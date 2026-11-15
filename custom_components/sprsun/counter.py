"""Counter rules without Home Assistant dependencies.

Callers supply binary values and datetimes in the configured local timezone.
"""

from datetime import datetime


class Counter:
    """Track rising edges, completed defrosts and calendar periods."""

    def __init__(self, reset_mode: str | None):
        self.reset_mode = reset_mode
        self.value = 0
        self.period: str | None = None
        self._defrost_start: datetime | None = None

    def _period_for(self, now: datetime) -> str | None:
        date_format = {
            "daily": "%Y-%m-%d",
            "monthly": "%Y-%m",
            "yearly": "%Y",
        }.get(self.reset_mode)
        return now.strftime(date_format) if date_format else None

    def restore(
        self,
        value: str | None,
        now: datetime,
        *,
        period: str | None = None,
        last_updated: datetime | None = None,
    ) -> None:
        self.period = self._period_for(now)
        try:
            self.value = int(float(value))
        except (TypeError, ValueError, OverflowError):
            self.value = 0
        if self.period is not None:
            if period is None and last_updated is not None:
                period = self._period_for(last_updated)
            if period != self.period:
                self.value = 0

    def reset_if_needed(self, now: datetime) -> bool:
        period = self._period_for(now)
        if period is None or period == self.period:
            return False
        self.value = 0
        self.period = period
        return True

    def handle_transition(
        self, old: bool | None, new: bool | None, now: datetime
    ) -> bool:
        if old is not False or new is not True:
            return False
        self.reset_if_needed(now)
        self.value += 1
        return True

    def handle_defrost(
        self, compressor: bool | None, fan: bool | None, now: datetime
    ) -> bool:
        if compressor is None or fan is None:
            self._defrost_start = None
            return False
        if compressor and not fan:
            if self._defrost_start is None:
                self._defrost_start = now
            return False
        completed = (
            self._defrost_start is not None
            and (now - self._defrost_start).total_seconds() >= 60
        )
        self._defrost_start = None
        if completed:
            self.reset_if_needed(now)
            self.value += 1
        return completed
