from datetime import date

import pytest

from core.conventions import (
    CalendarName,
    RollRule,
    add_business_days,
    add_months,
    adjust,
    basis_days,
    business_days_between,
    holidays,
    is_business_day,
    schedule,
    third_friday,
    year_fraction,
)
from core.types import DayCount, money


def test_act360_and_act365():
    """91 days between 2026-01-01 and 2026-04-02: 91/360 = 0.252778, 91/365 = 0.249315."""
    d1, d2 = date(2026, 1, 1), date(2026, 4, 2)
    assert year_fraction(d1, d2, DayCount.ACT360) == pytest.approx(91 / 360)
    assert year_fraction(d1, d2, DayCount.ACT365F) == pytest.approx(91 / 365)


def test_thirty360():
    """2026-01-31 to 2026-03-31: D1=30, D2=31 -> 30; 360*0 + 30*2 + 0 = 60 -> 60/360."""
    assert year_fraction(date(2026, 1, 31), date(2026, 3, 31), DayCount.THIRTY360) == pytest.approx(
        60 / 360
    )


def test_actact_spans_leap_year():
    """2023-07-01 to 2024-07-01: 184/365 (rest of 2023) + 182/366 (to 1 Jul 2024)."""
    got = year_fraction(date(2023, 7, 1), date(2024, 7, 1), DayCount.ACTACT)
    assert got == pytest.approx(184 / 365 + 182 / 366)


def test_negative_year_fraction():
    d1, d2 = date(2026, 1, 1), date(2026, 7, 1)
    for dc in DayCount:
        assert year_fraction(d2, d1, dc) == pytest.approx(-year_fraction(d1, d2, dc))


def test_basis_days():
    assert basis_days(DayCount.ACT360) == 360
    assert basis_days(DayCount.ACT365F) == 365


def test_us_holidays_2026():
    """NYSE 2026: Thanksgiving is the 4th Thursday of November = 26 Nov; Independence Day
    (Sat 4 Jul) is observed Friday 3 Jul; Good Friday is 3 Apr (Easter 5 Apr)."""
    h = holidays(CalendarName.US, 2026)
    assert date(2026, 11, 26) in h
    assert date(2026, 7, 3) in h
    assert date(2026, 4, 3) in h
    assert not is_business_day(date(2026, 11, 26), CalendarName.US)
    assert is_business_day(date(2026, 11, 27), CalendarName.US)


def test_target_and_uk_holidays():
    """Easter 2026 is 5 Apr: Good Friday 3 Apr, Easter Monday 6 Apr. TARGET closes 1 May;
    UK has the 25 May spring bank holiday and 31 Aug summer bank holiday."""
    assert date(2026, 4, 6) in holidays(CalendarName.TARGET, 2026)
    assert date(2026, 5, 1) in holidays(CalendarName.TARGET, 2026)
    uk = holidays(CalendarName.UK, 2026)
    assert date(2026, 5, 25) in uk
    assert date(2026, 8, 31) in uk
    # Christmas 2026 is Friday: 25 Dec off; Boxing Day Sat 26 -> Monday 28 Dec.
    assert date(2026, 12, 25) in uk
    assert date(2026, 12, 28) in uk


def test_japan_holidays():
    """2026: Coming of Age = 2nd Monday Jan = 12 Jan; vernal equinox 20 Mar; exchange closed
    2-3 Jan."""
    jp = holidays(CalendarName.JAPAN, 2026)
    assert date(2026, 1, 12) in jp
    assert date(2026, 3, 20) in jp
    assert date(2026, 1, 2) in jp


def test_add_business_days_skips_weekend_and_holiday():
    """Wed 25 Nov 2026 + 2 US business days: Thu 26 Nov is Thanksgiving, so Fri 27 -> Mon 30."""
    assert add_business_days(date(2026, 11, 25), 2, CalendarName.US) == date(2026, 11, 30)
    assert add_business_days(date(2026, 11, 30), -2, CalendarName.US) == date(2026, 11, 25)
    assert add_business_days(date(2026, 11, 25), 0, CalendarName.US) == date(2026, 11, 25)


def test_business_days_between():
    """Mon 16 Nov to Mon 23 Nov 2026 on the US calendar: 5 business days in [d1, d2)."""
    assert business_days_between(date(2026, 11, 16), date(2026, 11, 23), CalendarName.US) == 5


def test_roll_rules():
    """Sat 31 Jan 2026: following -> Mon 2 Feb; preceding -> Fri 30 Jan; modified following
    crosses the month so goes back to Fri 30 Jan."""
    d = date(2026, 1, 31)
    cal = CalendarName.TARGET
    assert adjust(d, RollRule.FOLLOWING, cal) == date(2026, 2, 2)
    assert adjust(d, RollRule.PRECEDING, cal) == date(2026, 1, 30)
    assert adjust(d, RollRule.MODIFIED_FOLLOWING, cal) == date(2026, 1, 30)
    assert adjust(date(2026, 1, 30), RollRule.FOLLOWING, cal) == date(2026, 1, 30)


def test_add_months_clamps():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 11, 30), 3) == date(2027, 2, 28)
    assert add_months(date(2026, 3, 15), -4) == date(2025, 11, 15)


def test_third_friday():
    """Dec 2026: 1 Dec is Tuesday, so Fridays are 4, 11, 18 -> third Friday is 18 Dec."""
    assert third_friday(2026, 12) == date(2026, 12, 18)
    assert third_friday(2026, 3) == date(2026, 3, 20)


def test_schedule_monthly():
    """Monthly from 15 Oct 2026 to 15 Jan 2027, modified following on TARGET."""
    s = schedule(date(2026, 10, 15), date(2027, 1, 15), 1)
    assert s == [date(2026, 11, 16), date(2026, 12, 15), date(2027, 1, 15)]


def test_money_half_even():
    """2.675 written as a decimal rounds half-even to 2.68 (7 is odd -> up); 2.665 -> 2.66."""
    assert money(2.675) == 2.68
    assert money(2.665) == 2.66
    assert money(0.125, 2) == 0.12
