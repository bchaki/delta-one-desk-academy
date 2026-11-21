"""Day counts, business-day calendars and roll rules.

Calendars are rule-based approximations of exchange/bank holidays, good for the synthetic
years (2020-2030). They are teaching calendars, not an official holiday source.
"""

from __future__ import annotations

import calendar as _cal
from datetime import date, timedelta
from enum import StrEnum
from functools import cache

from dateutil.easter import easter

from core.types import DayCount

# --------------------------------------------------------------------------- day counts


def _thirty_360(d1: date, d2: date) -> float:
    """30/360 (Bond Basis, US): days = 360(Y2-Y1) + 30(M2-M1) + (D2-D1)."""
    dd1 = min(d1.day, 30)
    dd2 = d2.day
    if dd2 == 31 and dd1 == 30:
        dd2 = 30
    days = 360 * (d2.year - d1.year) + 30 * (d2.month - d1.month) + (dd2 - dd1)
    return days / 360.0


def _act_act(d1: date, d2: date) -> float:
    """ACT/ACT (ISDA): each calendar-year slice is divided by 365 or 366 days."""
    if d2 < d1:
        return -_act_act(d2, d1)
    total = 0.0
    cur = d1
    while cur < d2:
        year_end = date(cur.year + 1, 1, 1)
        stop = min(d2, year_end)
        total += (stop - cur).days / (366 if _cal.isleap(cur.year) else 365)
        cur = stop
    return total


def year_fraction(d1: date, d2: date, dc: DayCount) -> float:
    """Year fraction tau between ``d1`` and ``d2`` under day count ``dc``.

    ACT/360: days/360. ACT/365F: days/365. 30/360 (US bond basis). ACT/ACT (ISDA).
    Negative if ``d2 < d1``.
    """
    if dc is DayCount.ACT360:
        return (d2 - d1).days / 360.0
    if dc is DayCount.ACT365F:
        return (d2 - d1).days / 365.0
    if dc is DayCount.THIRTY360:
        return _thirty_360(d1, d2) if d2 >= d1 else -_thirty_360(d2, d1)
    if dc is DayCount.ACTACT:
        return _act_act(d1, d2)
    raise ValueError(f"unknown day count {dc}")


def basis_days(dc: DayCount) -> int:
    """Denominator used for simple accruals: 360 for ACT/360 and 30/360, else 365."""
    return 360 if dc in (DayCount.ACT360, DayCount.THIRTY360) else 365


# --------------------------------------------------------------------------- calendars


class CalendarName(StrEnum):
    US = "US"
    TARGET = "TARGET"
    UK = "UK"
    JAPAN = "JAPAN"


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """n-th (1-based) given weekday (Mon=0) of a month."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year, month, _cal.monthrange(year, month)[1])
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed_us(d: date) -> date:
    """US observed rule: Saturday -> Friday, Sunday -> Monday."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def _next_weekday_if_weekend(d: date) -> date:
    """UK substitute rule: weekend holiday moves to the following Monday."""
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _us_holidays(y: int) -> set[date]:
    gf = easter(y) - timedelta(days=2)
    hol = {
        _observed_us(date(y, 1, 1)),
        _nth_weekday(y, 1, 0, 3),  # MLK
        _nth_weekday(y, 2, 0, 3),  # Presidents
        gf,
        _last_weekday(y, 5, 0),  # Memorial
        _observed_us(date(y, 6, 19)),
        _observed_us(date(y, 7, 4)),
        _nth_weekday(y, 9, 0, 1),  # Labor
        _nth_weekday(y, 11, 3, 4),  # Thanksgiving
        _observed_us(date(y, 12, 25)),
    }
    # An observed New Year's Day falling on 31 Dec of the previous year is not a market
    # holiday under NYSE rules; drop it when the observed date leaves the year.
    return {d for d in hol if d.year == y}


def _target_holidays(y: int) -> set[date]:
    e = easter(y)
    return {
        date(y, 1, 1),
        e - timedelta(days=2),
        e + timedelta(days=1),
        date(y, 5, 1),
        date(y, 12, 25),
        date(y, 12, 26),
    }


def _uk_holidays(y: int) -> set[date]:
    e = easter(y)
    xmas = _next_weekday_if_weekend(date(y, 12, 25))
    boxing = date(y, 12, 26)
    boxing = _next_weekday_if_weekend(boxing)
    if boxing == xmas:  # Christmas on Fri/Sat... Boxing substitute lands after Christmas sub
        boxing += timedelta(days=1)
        boxing = _next_weekday_if_weekend(boxing)
    return {
        _next_weekday_if_weekend(date(y, 1, 1)),
        e - timedelta(days=2),
        e + timedelta(days=1),
        _nth_weekday(y, 5, 0, 1),
        _last_weekday(y, 5, 0),
        _last_weekday(y, 8, 0),
        xmas,
        boxing,
    }


def _equinox_day(year: int, spring: bool) -> int:
    base = 20.8431 if spring else 23.2488
    return int(base + 0.242194 * (year - 1980) - ((year - 1980) // 4))


def _japan_holidays(y: int) -> set[date]:
    fixed = [
        date(y, 1, 1),
        date(y, 2, 11),
        date(y, 2, 23),
        date(y, 3, _equinox_day(y, True)),
        date(y, 4, 29),
        date(y, 5, 3),
        date(y, 5, 4),
        date(y, 5, 5),
        date(y, 8, 11),
        date(y, 9, _equinox_day(y, False)),
        date(y, 11, 3),
        date(y, 11, 23),
    ]
    hol = set(fixed)
    # Substitute holiday: a holiday on Sunday moves to the next day not already a holiday.
    for d in fixed:
        if d.weekday() == 6:
            s = d + timedelta(days=1)
            while s in hol:
                s += timedelta(days=1)
            hol.add(s)
    hol |= {
        _nth_weekday(y, 1, 0, 2),  # Coming of Age
        _nth_weekday(y, 7, 0, 3),  # Marine Day
        _nth_weekday(y, 9, 0, 3),  # Respect for the Aged
        _nth_weekday(y, 10, 0, 2),  # Sports Day
    }
    # Exchange closures: 2-3 Jan and 31 Dec.
    hol |= {date(y, 1, 2), date(y, 1, 3), date(y, 12, 31)}
    return hol


_HOLIDAY_FUNCS = {
    CalendarName.US: _us_holidays,
    CalendarName.TARGET: _target_holidays,
    CalendarName.UK: _uk_holidays,
    CalendarName.JAPAN: _japan_holidays,
}


@cache
def holidays(cal: CalendarName, year: int) -> frozenset[date]:
    """Holidays for calendar ``cal`` in ``year`` (rule-based teaching approximation)."""
    return frozenset(_HOLIDAY_FUNCS[cal](year))


def is_business_day(d: date, cal: CalendarName) -> bool:
    """True if ``d`` is a weekday and not a holiday on ``cal``."""
    return d.weekday() < 5 and d not in holidays(cal, d.year)


def add_business_days(d: date, n: int, cal: CalendarName) -> date:
    """Move ``d`` by ``n`` business days (negative goes back). ``n = 0`` returns ``d`` unchanged."""
    step = 1 if n >= 0 else -1
    remaining = abs(n)
    cur = d
    while remaining:
        cur += timedelta(days=step)
        if is_business_day(cur, cal):
            remaining -= 1
    return cur


def business_days_between(d1: date, d2: date, cal: CalendarName) -> int:
    """Number of business days in the half-open interval [d1, d2)."""
    if d2 < d1:
        return -business_days_between(d2, d1, cal)
    n = 0
    cur = d1
    while cur < d2:
        if is_business_day(cur, cal):
            n += 1
        cur += timedelta(days=1)
    return n


def business_days(start: date, end: date, cal: CalendarName) -> list[date]:
    """All business days in [start, end] inclusive."""
    out = []
    cur = start
    while cur <= end:
        if is_business_day(cur, cal):
            out.append(cur)
        cur += timedelta(days=1)
    return out


# --------------------------------------------------------------------------- roll rules


class RollRule(StrEnum):
    FOLLOWING = "following"
    MODIFIED_FOLLOWING = "modified_following"
    PRECEDING = "preceding"


def adjust(d: date, rule: RollRule, cal: CalendarName) -> date:
    """Adjust a non-business day to a business day under ``rule``.

    Following: next business day. Preceding: previous business day. Modified following:
    following, unless that crosses into the next month, in which case preceding.
    """
    if is_business_day(d, cal):
        return d
    if rule is RollRule.PRECEDING:
        return add_business_days(d, -1, cal)
    fwd = add_business_days(d, 1, cal)
    if rule is RollRule.FOLLOWING:
        return fwd
    if fwd.month != d.month:
        return add_business_days(d, -1, cal)
    return fwd


def add_months(d: date, months: int) -> date:
    """Calendar month shift, clamping the day to the end of the target month."""
    m = d.month - 1 + months
    y = d.year + m // 12
    mo = m % 12 + 1
    return date(y, mo, min(d.day, _cal.monthrange(y, mo)[1]))


def third_friday(year: int, month: int) -> date:
    """Third Friday of a month (standard index futures expiry day, before holiday roll)."""
    return _nth_weekday(year, month, 4, 3)


def schedule(
    start: date,
    end: date,
    months: int,
    rule: RollRule = RollRule.MODIFIED_FOLLOWING,
    cal: CalendarName = CalendarName.TARGET,
) -> list[date]:
    """Regular schedule of adjusted dates after ``start`` up to and including ``end``.

    Unadjusted dates are ``start + k*months``; each is rolled with ``rule`` on ``cal``.
    The final date is forced to the adjusted ``end`` if the grid does not land on it.
    """
    out: list[date] = []
    k = 1
    while True:
        raw = add_months(start, k * months)
        if raw >= end:
            break
        out.append(adjust(raw, rule, cal))
        k += 1
    last = adjust(end, rule, cal)
    if not out or out[-1] != last:
        out.append(last)
    return out
