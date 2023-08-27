# Copyright 2022-2023 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

from datetime import datetime, timedelta, timezone

from django.shortcuts import reverse
from django.utils.html import mark_safe
from django.utils.timezone import now


def plural(n):
    if n > 1:
        return 's'
    return ''


def space(a, b):
    if a:
        a += ' '
    return a + b


def short_fmt(nbr, unit):
    if unit in ('m', 's'):
        return '%02d%s' % (nbr, unit)
    return '%s%s' % (nbr, unit)


def human_short_datetime(d):
    years = d.days // 365
    days = d.days % 365
    hours = d.seconds // 60 // 60
    minutes = d.seconds // 60 % 60
    seconds = d.seconds % 60

    nbrs = [years, days, hours, minutes, seconds]
    units = ['y', 'd', 'h', 'm', 's']

    for i in range(len(nbrs) - 1):
        if nbrs[i]:
            return '%s%s' % (short_fmt(nbrs[i], units[i]).lstrip('0'), short_fmt(nbrs[i + 1], units[i + 1]))
    return '%ss' % seconds


def human_datetime(d, short=False):
    if not d:
        return d
    if short:
        return human_short_datetime(d)

    s = ''
    years = d.days // 365
    days = d.days % 365

    if years:
        s = space(s, '%s year%s' % (years, plural(years)))

    if days:
        s = space(s, '%s day%s' % (days, plural(days)))

    hours = d.seconds // 60 // 60
    minutes = d.seconds // 60 % 60
    seconds = d.seconds % 60

    if hours:
        s = space(s, '%s hour%s' % (hours, plural(hours)))

    if minutes:
        s = space(s, '%s minute%s' % (minutes, plural(minutes)))

    if seconds:
        s = space(s, '%s second%s' % (seconds, plural(seconds)))

    return s


def human_dt(d, short=False):
    if not d:
        return d
    dt = d - now()

    zero = timedelta()
    if dt < zero:
        dt_str = human_datetime(-dt, short)
        return dt_str + ' ago'
    elif dt > zero:
        dt_str = human_datetime(dt, short)
        return 'in ' + dt_str
    return 'now'


def get_unit(n):
    units = ['', 'k', 'M', 'G', 'T', 'P']
    unit_no = 0
    while n >= 1000:
        unit_no += 1
        n /= 1000
    return 10 ** (unit_no * 3), units[unit_no]


def human_filesize(n):
    factor, unit = get_unit(n)
    return '%0.1f%sB' % (n / factor, unit)


def reverse_no_escape(url, args):
    assert isinstance(args, (list, tuple))
    assert len(args) == 1
    arg = args[0]

    # unquote since Django's reverse will quote
    url = reverse(url)
    url = mark_safe(url + arg)
    return url


def http_date_parser(d):
    if d is None:
        return None
    assert isinstance(d, str)
    try:
        _, day, month, year, t, _ = d.strip().split()
        day = int(day)
        MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
        month = MONTHS.index(month.lower()) + 1
        year = int(year)

        hour, minute, second = t.split(':')
        hour = int(hour)
        minute = int(minute)
        second = int(second)

        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    except (ValueError, IndexError):
        return None


def http_date_format(d):
    # Locale independant formatting
    assert isinstance(d, datetime)
    DOW = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    dow = DOW[d.weekday()]

    MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
    month = MONTHS[d.month - 1]

    s = f'{dow}, {d.day} {month} {d.year}'
    s += ' %02d:%02d:%02d GMT' % (d.hour, d.minute, d.second)
    return s
