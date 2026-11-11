"""Parse natural-language date strings into ``datetime.date`` objects."""

import calendar
import re
from datetime import date, timedelta

__all__ = ["parse"]

_MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

_WEEKDAYS = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tues": 1,
    "tue": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thurs": 3,
    "thur": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

# Keyword -> offset in days from today.
_KEYWORDS = {
    "today": 0,
    "now": 0,
    "tonight": 0,
    "tomorrow": 1,
    "yesterday": -1,
    "day after tomorrow": 2,
    "day before yesterday": -2,
}

# Unit -> (months, days).
_UNITS = {
    "day": (0, 1),
    "week": (0, 7),
    "fortnight": (0, 14),
    "month": (1, 0),
    "year": (12, 0),
}

_ONES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

_ORDINALS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
    "twentieth": 20,
    "thirtieth": 30,
}
for _prefix, _base in (("twenty", 20), ("thirty", 30)):
    for _word, _value in list(_ORDINALS.items())[:9]:
        if _base + _value <= 31:
            _ORDINALS[f"{_prefix}-{_word}"] = _base + _value
            _ORDINALS[f"{_prefix} {_word}"] = _base + _value


def _alternation(words: dict[str, int]) -> str:
    return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))


_MONTH_RE = rf"(?P<month>{_alternation(_MONTHS)})\.?"
_DAY_RE = rf"(?P<day>\d{{1,2}}(?:st|nd|rd|th)?|{_alternation(_ORDINALS)})"
_YEAR_RE = r"(?P<year>\d{4})"
_WEEKDAY_RE = rf"(?:{_alternation(_WEEKDAYS)})\.?"

_NAMED_DATE_PATTERNS = [
    re.compile(rf"{_MONTH_RE}\s+(?:the\s+)?{_DAY_RE}(?:\s+{_YEAR_RE})?"),
    re.compile(rf"{_DAY_RE}\s+(?:of\s+)?{_MONTH_RE}(?:\s+{_YEAR_RE})?"),
    re.compile(rf"{_MONTH_RE}\s+{_YEAR_RE}"),
]


def _normalize(s: str) -> str:
    text = re.sub(r"\s+", " ", s.strip().lower())
    text = text.rstrip(".").strip()
    text = text.removeprefix("the ")
    return text


def _parse_number(text: str) -> int | None:
    text = text.strip()
    text = text.removesuffix(" of")
    if text.isdigit():
        return int(text)
    if text in ("a", "an", "one"):
        return 1
    if text in ("a couple", "couple"):
        return 2
    words = re.split(r"[\s-]+", text)
    if len(words) == 1:
        if words[0] in _ONES:
            return _ONES[words[0]]
        if words[0] in _TENS:
            return _TENS[words[0]]
    if len(words) == 2 and words[0] in _TENS and 1 <= _ONES.get(words[1], 0) <= 9:
        return _TENS[words[0]] + _ONES[words[1]]
    return None


def _parse_duration(text: str) -> tuple[int, int] | None:
    """Parse e.g. "1 year, 2 months and 3 days" into (months, days)."""
    parts = [p for p in re.split(r"\s*(?:,|\band\b)\s*", text) if p]
    if not parts:
        return None
    months = days = 0
    for part in parts:
        m = re.fullmatch(
            r"(?:(.+?)\s*)?(?<![a-z])(day|week|fortnight|month|year)s?", part
        )
        if m is None:
            return None
        n = 1 if m.group(1) is None else _parse_number(m.group(1))
        if n is None:
            return None
        unit_months, unit_days = _UNITS[m.group(2)]
        months += n * unit_months
        days += n * unit_days
    return months, days


def _add_months(d: date, n: int) -> date:
    total = d.year * 12 + (d.month - 1) + n
    year, month = divmod(total, 12)
    month += 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _shift(d: date, duration: tuple[int, int], sign: int) -> date:
    months, days = duration
    return _add_months(d, sign * months) + timedelta(days=sign * days)


def _make_date(year: int, month: int, day: int) -> date:
    if year < 100:
        year += 2000
    return date(year, month, day)


def _parse_absolute(text: str, today: date) -> date | None:
    text = re.sub(r"\s+", " ", text.replace(",", " ")).strip()

    # Optional leading weekday, e.g. "Monday, December 1, 2025".
    m = re.fullmatch(rf"{_WEEKDAY_RE}\s+(.+)", text)
    if m is not None:
        text = m.group(1)

    # ISO-style: 2025-12-01, 2025/12/01, 2025.12.01
    m = re.fullmatch(r"(\d{4})([-/.])(\d{1,2})\2(\d{1,2})", text)
    if m is not None:
        return _make_date(int(m.group(1)), int(m.group(3)), int(m.group(4)))

    # US-style: 12/01/2025, 12-01-25, 12/1 (falls back to D/M/Y if needed)
    m = re.fullmatch(r"(\d{1,2})([-/.])(\d{1,2})(?:\2(\d{4}|\d{2}))?", text)
    if m is not None:
        first, second = int(m.group(1)), int(m.group(3))
        year = int(m.group(4)) if m.group(4) else today.year
        if first > 12 and second <= 12:
            first, second = second, first
        return _make_date(year, first, second)

    # Named months: "December 1st, 2025", "1 Dec 2025", "1st of December", ...
    for pattern in _NAMED_DATE_PATTERNS:
        m = pattern.fullmatch(text)
        if m is None:
            continue
        groups = m.groupdict()
        month = _MONTHS[groups["month"]]
        year = int(groups["year"]) if groups.get("year") else today.year
        day_text = groups.get("day")
        if day_text is None:
            day = 1
        elif day_text in _ORDINALS:
            day = _ORDINALS[day_text]
        else:
            day = int(re.sub(r"\D", "", day_text))
        return _make_date(year, month, day)

    return None


def _parse(s: str, today: date) -> date:
    text = _normalize(s)
    if not text:
        raise ValueError("empty date string")

    if text in _KEYWORDS:
        return today + timedelta(days=_KEYWORDS[text])

    # "in 3 days"
    m = re.fullmatch(r"in (.+)", text)
    if m is not None:
        duration = _parse_duration(m.group(1))
        if duration is not None:
            return _shift(today, duration, 1)

    # "3 days ago", "2 weeks later"
    m = re.fullmatch(r"(.+?) (ago|later|hence)", text)
    if m is not None:
        duration = _parse_duration(m.group(1))
        if duration is not None:
            return _shift(today, duration, -1 if m.group(2) == "ago" else 1)

    # "5 days before December 1st, 2025", "two weeks from tomorrow"
    m = re.fullmatch(r"(.+?) (before|prior to|after|from) (.+)", text)
    if m is not None:
        duration = _parse_duration(m.group(1))
        if duration is not None:
            anchor = _parse(m.group(3), today)
            sign = -1 if m.group(2) in ("before", "prior to") else 1
            return _shift(anchor, duration, sign)

    # "next Tuesday", "last week", "this Friday"
    m = re.fullmatch(r"(next|coming|last|previous|past|this) (\w+)", text)
    if m is not None:
        modifier, word = m.groups()
        if word in _WEEKDAYS:
            target = _WEEKDAYS[word]
            if modifier == "this":
                offset = (target - today.weekday()) % 7
            elif modifier in ("next", "coming"):
                offset = (target - today.weekday() - 1) % 7 + 1
            else:
                offset = -((today.weekday() - target - 1) % 7 + 1)
            return today + timedelta(days=offset)
        unit = word.removesuffix("s")
        if unit in _UNITS:
            if modifier == "this":
                return today
            sign = 1 if modifier in ("next", "coming") else -1
            return _shift(today, _UNITS[unit], sign)

    # Bare weekday: the next occurrence, counting today.
    weekday = text.rstrip(".")
    if weekday in _WEEKDAYS:
        return today + timedelta(days=(_WEEKDAYS[weekday] - today.weekday()) % 7)

    result = _parse_absolute(text, today)
    if result is not None:
        return result

    raise ValueError(f"unrecognized date: {s!r}")


def parse(s: str, today: date | None = None) -> date:
    """Parse a natural-language date string into a ``date``.

    Relative expressions are resolved against ``today``, which defaults to the
    current date. Raises ``ValueError`` if the string is not a recognized date.
    """
    if today is None:
        today = date.today()
    try:
        return _parse(s, today)
    except OverflowError as e:
        raise ValueError(f"date out of range: {s!r}") from e
