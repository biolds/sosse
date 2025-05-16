# Copyright 2022-2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.exceptions import ValidationError
from django.shortcuts import reverse
from django.utils.html import mark_safe
from django.utils.timezone import now


def plural(n):
    if n > 1:
        return "s"
    return ""


def space(a, b):
    if a:
        a += " "
    return a + b


def short_fmt(nbr, unit):
    if unit in ("m", "s"):
        return f"{nbr:02d}{unit}"
    return f"{nbr}{unit}"


def human_short_datetime(d):
    years = d.days // 365
    days = d.days % 365
    hours = d.seconds // 60 // 60
    minutes = d.seconds // 60 % 60
    seconds = d.seconds % 60

    nbrs = [years, days, hours, minutes, seconds]
    units = ["y", "d", "h", "m", "s"]

    for i in range(len(nbrs) - 1):
        if nbrs[i]:
            return short_fmt(nbrs[i], units[i]).lstrip("0") + short_fmt(nbrs[i + 1], units[i + 1])
    return f"{seconds}s"


def human_datetime(d, short=False):
    if not d:
        return d
    if short:
        return human_short_datetime(d)

    s = ""
    years = d.days // 365
    days = d.days % 365

    if years:
        s = space(s, f"{years} year{plural(years)}")

    if days:
        s = space(s, f"{days} day{plural(days)}")

    hours = d.seconds // 60 // 60
    minutes = d.seconds // 60 % 60
    seconds = d.seconds % 60

    if hours:
        s = space(s, f"{hours} hour{plural(hours)}")

    if minutes:
        s = space(s, f"{minutes} minute{plural(minutes)}")

    if seconds:
        s = space(s, f"{seconds} second{plural(seconds)}")

    return s


def human_dt(d, short=False):
    if not d:
        return d
    dt = d - now()

    zero = timedelta()
    if dt < zero:
        dt_str = human_datetime(-dt, short)
        return dt_str + " ago"
    elif dt > zero:
        dt_str = human_datetime(dt, short)
        return "in " + dt_str
    return "now"


def get_unit(n):
    units = ["", "k", "M", "G", "T", "P"]
    unit_no = 0
    while n >= 1000:
        unit_no += 1
        n /= 1000
    return 10 ** (unit_no * 3), units[unit_no]


def human_nb(n):
    factor, unit = get_unit(n)
    return f"{n / factor:.0f}{unit}"


def human_filesize(n):
    factor, unit = get_unit(n)
    return f"{n / factor:0.1f}{unit}B"


def reverse_no_escape(url, args):
    if not isinstance(args, (list, tuple)):
        raise ValueError("args must be a list or a tuple")
    if len(args) != 1:
        raise ValueError("args must have exactly one element")
    arg = args[0]

    # unquote since Django's reverse will quote
    url = reverse(url)
    url = mark_safe(url + arg)
    return url


def http_date_parser(d):
    if d is None:
        return None
    if not isinstance(d, str):
        raise ValueError("d must be a string")
    try:
        _, day, month, year, t, _ = d.strip().split()
        day = int(day)
        MONTHS = (
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        )
        month = MONTHS.index(month.lower()) + 1
        year = int(year)

        hour, minute, second = t.split(":")
        hour = int(hour)
        minute = int(minute)
        second = int(second)

        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    except (ValueError, IndexError):
        return None


def http_date_format(d):
    # Locale independant formatting
    if not isinstance(d, datetime):
        raise ValueError("d must be a datetime object")
    DOW = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    dow = DOW[d.weekday()]

    MONTHS = (
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    )
    month = MONTHS[d.month - 1]

    s = f"{dow}, {d.day} {month} {d.year}"
    s += " %02d:%02d:%02d GMT" % (d.hour, d.minute, d.second)
    return s


MIMETYPE_ICONS = None


def mimetype_icon(mime: str | None) -> str:
    global MIMETYPE_ICONS
    if not MIMETYPE_ICONS:
        mime_file = Path(__file__).parent / "deps/unicode_mime_icons/unicode_mime_icons.json"
        with open(mime_file, "rb") as fd:
            MIMETYPE_ICONS = json.load(fd)

    if mime:
        for regex, icon in MIMETYPE_ICONS.items():
            if re.match(regex, mime):
                return icon
    return "🗎"


def build_multiline_re(r):
    # Converts a multiline regex with comments to a single line regex
    url_regexs = [line.strip() for line in r.splitlines()]
    url_regexs = [line for line in url_regexs if not line.startswith("#") and line]
    match len(url_regexs):
        case 0:
            return ""
        case 1:
            return url_regexs[0]
        case _:
            return "(" + "|".join(url_regexs) + ")"


def validate_multiline_re(r):
    r = build_multiline_re(r)
    try:
        re.match(r, "")
    except re.error as e:
        raise ValidationError(str(e))
