from datetime import date, timedelta
import os

from django.conf import settings
from django.db import connection, models
from django.shortcuts import render
from django.utils.timezone import now
from langdetect.detector_factory import PROFILES_DIRECTORY
import pygal

from .models import CrawlerStats, Document
from .views import get_context


def get_unit(n):
    units = ['', 'k', 'M', 'G', 'T', 'P']
    unit_no = 0
    while n >= 1000:
        unit_no += 1
        n /= 1000
    return 10 ** (unit_no * 3), units[unit_no]


def filesizeformat(n):
    factor, unit = get_unit(n)
    return '%0.1f%sB' % (n / factor, unit)


def datetime_graph(pygal_style, freq, data, col, _now):
    if freq == CrawlerStats.MINUTELY:
        start = _now - timedelta(hours=23)
        start = start.replace(minute=0, second=0, microsecond=0)
        timespan = timedelta(hours=24)
        dt = timedelta(hours=6)
        format_str = '%H:%M'
        x_title = 'UTC time'

        x_labels = [start]
        t = start
        while timespan.total_seconds() > 0:
            t += dt
            timespan -= dt
            if freq == CrawlerStats.DAILY:
                t = t.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            x_labels.append(t)
        cls = pygal.DateTimeLine
    else:
        start = _now - timedelta(days=364)
        start = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        x_labels = [start]
        t = start
        for i in range(1, 7):
            month = t.month + (i * 2)
            year = int((month - 1) / 12)
            month = ((month - 1) % 12) + 1
            d = date(year=t.year + year, month=month, day=1)
            x_labels.append(d)

        format_str = '%b'
        x_title = None
        cls = pygal.DateLine

    g = cls(style=pygal_style, disable_xml_declaration=True,
                                     truncate_label=-1, show_legend=False, fill=True,
                                     x_value_formatter=lambda dt: dt.strftime(format_str),
                                     x_title=x_title)
    g.x_labels = x_labels
    stats_max = data.aggregate(m=models.Max(col)).get('m', 0) or 0
    factor, unit = get_unit(stats_max)

    entries = []
    for entry in data:
        val = getattr(entry, col)
        if val is not None:
            entries.append((entry.t.timestamp(), val / factor))

    if entries == []:
        entries = [(start, 0), (_now, 0)]

    g.add('', entries)
    return g


def crawler_stats(pygal_style, freq):
    _now = now()
    if freq == CrawlerStats.MINUTELY:
        dt = _now - timedelta(days=1)
    else:
        dt = _now - timedelta(days=365)
    data = CrawlerStats.objects.filter(t__gte=dt, freq=freq).order_by('t')

    if data.count() < 2:
        return {}

    # Doc count minutely
    doc_count = datetime_graph(pygal_style, freq, data, 'doc_count', _now)
    factor, unit = get_unit(data.aggregate(m=models.Max('doc_count')).get('m', 0) or 0)
    doc_count.title = 'Doc count'
    if unit:
        doc_count.title += ' (%s)' % unit
    doc_count = doc_count.render()

    # Indexing speed minutely
    idx_speed_data = data.annotate(speed=models.F('indexing_speed') / 60)
    idx_speed = datetime_graph(pygal_style, freq, idx_speed_data, 'speed', _now)
    factor, unit = get_unit(data.aggregate(m=models.Max('indexing_speed')).get('m', 0) or 0 / 60.0)
    if not unit:
        unit = 'doc'
    idx_speed.title = 'Indexing speed (%s/s)' % unit
    idx_speed = idx_speed.render()

    # Url queued minutely
    url_queue = datetime_graph(pygal_style, freq, data, 'url_queued_count', _now)
    factor, unit = get_unit(data.aggregate(m=models.Max('url_queued_count')).get('m', 1))
    url_queue.title = 'URL queue size'
    if unit:
        url_queue.title += ' (%s)' % unit
    url_queue = url_queue.render()
    freq = freq.lower()
    return {
        '%s_doc_count' % freq: doc_count,
        '%s_idx_speed' % freq: idx_speed,
        '%s_url_queue' % freq: url_queue,
    }


def stats(request):
    pygal_style = pygal.style.Style(
        background='transparent',
        plot_background='transparent',
        title_font_size=40,
        legend_font_size=40,
        label_font_size=35,
        major_label_font_size=35,
    )

    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_database_size(%s)', [settings.DATABASES['default']['NAME']])
        db_size = cursor.fetchall()[0][0]

    doc_count = Document.objects.count()
    indexed_langs = Document.objects.exclude(lang_iso_639_1__isnull=True).values('lang_iso_639_1').annotate(count=models.Count('lang_iso_639_1')).order_by('-count')

    # Language chart
    lang_chart = None
    if indexed_langs:
        lang_chart = pygal.Bar(style=pygal_style, disable_xml_declaration=True)
        lang_chart.title = "Document's language"

        factor, unit = get_unit(indexed_langs[0]['count'])
        if unit:
            lang_chart.title += ' (%s)' % unit

        for lang in indexed_langs[:8]:
            lang_iso = lang['lang_iso_639_1']
            lang_desc = settings.MYSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {})
            title = lang_iso.title()
            if lang_desc.get('flag'):
                title = title + ' ' + lang_desc['flag']
            percent = lang['count'] / factor
            lang_chart.add(title, percent)
        lang_chart = lang_chart.render()

    # HDD chart
    statvfs = os.statvfs('/var/lib')
    hdd_size = statvfs.f_frsize * statvfs.f_blocks
    hdd_free = statvfs.f_frsize * statvfs.f_bavail
    hdd_other = hdd_size - hdd_free - db_size
    factor, unit = get_unit(hdd_size)

    hdd_pie = pygal.Pie(style=pygal_style, disable_xml_declaration=True)
    hdd_pie.title = 'HDD size (total %s)' % filesizeformat(hdd_size)
    hdd_pie.add('DB(%s)' % filesizeformat(db_size), db_size)
    hdd_pie.add('Other(%s)' % filesizeformat(hdd_other), hdd_other)
    hdd_pie.add('Free(%s)' % filesizeformat(hdd_free), hdd_free)

    # Crawler stats
    context = get_context({
        'title': 'Statistics',

        # index
        'doc_count': doc_count,
        'lang_count': len(indexed_langs),
        'db_size': filesizeformat(db_size),
        'doc_size': 0 if doc_count == 0 else filesizeformat(db_size / doc_count),
        'lang_recognizable': len(os.listdir(PROFILES_DIRECTORY)),
        'lang_parsable': [l.title() for l in sorted(Document.get_supported_langs())],
        'lang_chart': lang_chart,
        'hdd_pie': hdd_pie.render(),
    })

    context.update(crawler_stats(pygal_style, CrawlerStats.MINUTELY))
    context.update(crawler_stats(pygal_style, CrawlerStats.DAILY))
    return render(request, 'se/stats.html', context)
