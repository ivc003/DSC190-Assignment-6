from datetime import date

import pytest

from nldate import parse

# Tuesday, November 10, 2026
TODAY = date(2026, 11, 10)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Examples from the spec
        ("5 days before December 1st, 2025", date(2025, 11, 26)),
        ("1 year and 2 months after yesterday", date(2028, 1, 9)),
        ("next Tuesday", date(2026, 11, 17)),
        ("two weeks from tomorrow", date(2026, 11, 25)),
        # Keywords
        ("today", date(2026, 11, 10)),
        ("tomorrow", date(2026, 11, 11)),
        ("yesterday", date(2026, 11, 9)),
        ("the day after tomorrow", date(2026, 11, 12)),
        ("the day before yesterday", date(2026, 11, 8)),
        # Absolute dates
        ("December 1st, 2025", date(2025, 12, 1)),
        ("December 1, 2025", date(2025, 12, 1)),
        ("Dec. 1 2025", date(2025, 12, 1)),
        ("1 December 2025", date(2025, 12, 1)),
        ("the 1st of December, 2025", date(2025, 12, 1)),
        ("December first, 2025", date(2025, 12, 1)),
        ("Monday, December 1, 2025", date(2025, 12, 1)),
        ("Dec 1", date(2026, 12, 1)),
        ("2025-12-01", date(2025, 12, 1)),
        ("12/01/2025", date(2025, 12, 1)),
        ("12/1/25", date(2025, 12, 1)),
        # Weekdays
        ("Tuesday", date(2026, 11, 10)),
        ("Friday", date(2026, 11, 13)),
        ("next Friday", date(2026, 11, 13)),
        ("last Tuesday", date(2026, 11, 3)),
        ("last Sunday", date(2026, 11, 8)),
        ("this Thursday", date(2026, 11, 12)),
        # Relative units
        ("next week", date(2026, 11, 17)),
        ("last month", date(2026, 10, 10)),
        ("next year", date(2027, 11, 10)),
        # Durations
        ("in 3 days", date(2026, 11, 13)),
        ("3 days ago", date(2026, 11, 7)),
        ("a week from now", date(2026, 11, 17)),
        ("in twenty-one days", date(2026, 12, 1)),
        ("in 1 year, 2 months and 3 days", date(2028, 1, 13)),
        ("3 weeks before next Friday", date(2026, 10, 23)),
        # Case and whitespace insensitivity
        ("  NEXT   tuesday  ", date(2026, 11, 17)),
    ],
)
def test_parse(text: str, expected: date) -> None:
    assert parse(text, today=TODAY) == expected


def test_month_arithmetic_clamps_to_end_of_month() -> None:
    assert parse("1 month after January 31, 2024", today=TODAY) == date(2024, 2, 29)


def test_today_defaults_to_current_date() -> None:
    assert parse("today") == date.today()


@pytest.mark.parametrize(
    "text",
    ["", "   ", "not a date", "February 30, 2025", "3 days", "next blursday"],
)
def test_invalid_input_raises_value_error(text: str) -> None:
    with pytest.raises(ValueError):
        parse(text, today=TODAY)
