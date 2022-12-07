from datetime import timedelta

from django.utils.timezone import now


def plural(n, short):
    if short:
        return ''
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
    count = 2

    s = ''
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
