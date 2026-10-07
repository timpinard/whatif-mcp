from datetime import date
from itertools import islice

from whatif_mcp.core.model import Frequency
from whatif_mcp.core.recurrence import occurrence_dates


def first_occurrences(start: date, frequency: Frequency, count: int) -> list[date]:
    return list(islice(occurrence_dates(start, frequency, None), count))


def test_AC12_calendar_stepping_stays_anchored() -> None:
    assert first_occurrences(date(2027, 1, 31), Frequency.MONTHLY, 4) == [
        date(2027, 1, 31),
        date(2027, 2, 28),
        date(2027, 3, 31),
        date(2027, 4, 30),
    ]
    assert date(2028, 2, 29) in first_occurrences(date(2027, 1, 31), Frequency.MONTHLY, 14)
    assert first_occurrences(date(2026, 11, 30), Frequency.QUARTERLY, 3) == [
        date(2026, 11, 30),
        date(2027, 2, 28),
        date(2027, 5, 30),
    ]
    assert first_occurrences(date(2026, 11, 30), Frequency.SEMIANNUAL, 3) == [
        date(2026, 11, 30),
        date(2027, 5, 30),
        date(2027, 11, 30),
    ]
    assert first_occurrences(date(2028, 2, 29), Frequency.ANNUAL, 5) == [
        date(2028, 2, 29),
        date(2029, 2, 28),
        date(2030, 2, 28),
        date(2031, 2, 28),
        date(2032, 2, 29),
    ]
    assert first_occurrences(date(2026, 10, 7), Frequency.WEEKLY, 3) == [
        date(2026, 10, 7),
        date(2026, 10, 14),
        date(2026, 10, 21),
    ]
    assert first_occurrences(date(2026, 10, 7), Frequency.BIWEEKLY, 3) == [
        date(2026, 10, 7),
        date(2026, 10, 21),
        date(2026, 11, 4),
    ]


def test_AC13_semimonthly_twice_every_month() -> None:
    assert first_occurrences(date(2026, 10, 20), Frequency.SEMIMONTHLY, 4) == [
        date(2026, 10, 20),
        date(2026, 11, 5),
        date(2026, 11, 20),
        date(2026, 12, 5),
    ]
    assert first_occurrences(date(2027, 1, 30), Frequency.SEMIMONTHLY, 5) == [
        date(2027, 1, 30),
        date(2027, 2, 15),
        date(2027, 2, 28),
        date(2027, 3, 15),
        date(2027, 3, 30),
    ]
    one_year = list(occurrence_dates(date(2026, 10, 1), Frequency.SEMIMONTHLY, date(2027, 9, 30)))
    assert len(one_year) == 24
