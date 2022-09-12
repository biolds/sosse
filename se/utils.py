def plural(n):
    if n > 1:
        return 's'
    return ''

def space(a, b):
    if a:
        a += ' '
    return a + b

def human_datetime(d):
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
