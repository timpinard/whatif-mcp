import calendar
from collections.abc import Iterator
from datetime import date, timedelta
from itertools import count

from whatif_mcp.core.model import Frequency

MONTHS_PER_YEAR = 12
SEMIMONTHLY_OFFSET_DAYS = 15
LAST_FIRST_HALF_DAY = 15

DAY_STEPS = {
    Frequency.WEEKLY: timedelta(days=7),
    Frequency.BIWEEKLY: timedelta(days=14),
}

MONTH_STEPS = {
    Frequency.MONTHLY: 1,
    Frequency.QUARTERLY: 3,
    Frequency.SEMIANNUAL: 6,
    Frequency.ANNUAL: 12,
}


def occurrence_dates(start: date, frequency: Frequency, end: date | None) -> Iterator[date]:
    for occurrence in _unbounded_dates(start, frequency):
        if end is not None and occurrence > end:
            return
        yield occurrence


def _unbounded_dates(start: date, frequency: Frequency) -> Iterator[date]:
    if frequency is Frequency.ONE_TIME:
        yield start
    elif frequency is Frequency.SEMIMONTHLY:
        yield from _semimonthly_dates(start)
    elif frequency in DAY_STEPS:
        step = DAY_STEPS[frequency]
        for index in count():
            yield start + step * index
    else:
        months = MONTH_STEPS[frequency]
        for index in count():
            yield _clamped_date(start.year, start.month + months * index, start.day)


def _semimonthly_dates(start: date) -> Iterator[date]:
    if start.day <= LAST_FIRST_HALF_DAY:
        second_day = start.day + SEMIMONTHLY_OFFSET_DAYS
    else:
        second_day = start.day - SEMIMONTHLY_OFFSET_DAYS
    days = sorted((start.day, second_day))
    for month_offset in count():
        for day in days:
            occurrence = _clamped_date(start.year, start.month + month_offset, day)
            if occurrence >= start:
                yield occurrence


def _clamped_date(year: int, unnormalized_month: int, day: int) -> date:
    year += (unnormalized_month - 1) // MONTHS_PER_YEAR
    month = (unnormalized_month - 1) % MONTHS_PER_YEAR + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last_day))
