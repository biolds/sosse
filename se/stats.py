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

from datetime import date, timedelta
import os

from django.conf import settings
from django.db import connection, models
from django.shortcuts import render, redirect, reverse
from django.utils.timezone import now
from langdetect.detector_factory import PROFILES_DIRECTORY
import pygal

from .login import login_required
from .models import CrawlerStats, Document, DAILY, MINUTELY
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


def datetime_graph(pygal_config, pygal_style, freq, data, col, _now):
    if freq == MINUTELY:
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
            if freq == DAILY:
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

    g = cls(pygal_config, style=pygal_style, disable_xml_declaration=True,
            truncate_label=-1, show_legend=False, fill=True,
            x_value_formatter=lambda dt: dt.strftime(format_str),
            x_title=x_title, range=(0, None))
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


def crawler_stats(pygal_config, pygal_style, freq):
    _now = now()
    if freq == MINUTELY:
        dt = _now - timedelta(days=1)
    else:
        dt = _now - timedelta(days=365)
    data = CrawlerStats.objects.filter(t__gte=dt, freq=freq).order_by('t')

    if data.count() < 1:
        return {}

    pygal_style.colors = ('#c6dcff',)
    pygal_style.title_font_size = 30

    # Doc count minutely
    doc_count = datetime_graph(pygal_config, pygal_style, freq, data, 'doc_count', _now)
    factor, unit = get_unit(data.aggregate(m=models.Max('doc_count')).get('m', 0) or 0)
    doc_count.title = 'Doc count'
    if unit:
        doc_count.title += ' (%s)' % unit
    doc_count = doc_count.render()

    # Processing speed minutely
    if freq == MINUTELY:
        idx_speed_data = data.annotate(speed=models.F('indexing_speed') / 60.0)
        factor, unit = get_unit(data.aggregate(m=models.Max('indexing_speed')).get('m', 0) or 0.0)
    else:
        idx_speed_data = data.annotate(speed=models.F('indexing_speed') / 60.0 / 60.0 / 24.0)
        factor, unit = get_unit(idx_speed_data.aggregate(m=models.Max('speed')).get('m', 0) or 0.0)
    idx_speed = datetime_graph(pygal_config, pygal_style, freq, idx_speed_data, 'speed', _now)
    if not unit:
        unit = 'doc'
    idx_speed.title = 'Processing speed (%s/s)' % unit
    idx_speed = idx_speed.render()

    # Url queued minutely
    url_queue = datetime_graph(pygal_config, pygal_style, freq, data, 'queued_url', _now)
    factor, unit = get_unit(data.aggregate(m=models.Max('queued_url')).get('m', 1))
    url_queue.title = 'URL queued'
    if unit:
        url_queue.title += ' (%s)' % unit
    url_queue = url_queue.render()
    freq = freq.lower()
    return {
        '%s_doc_count' % freq: doc_count,
        '%s_idx_speed' % freq: idx_speed,
        '%s_url_queue' % freq: url_queue,
    }


@login_required
def stats(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect(reverse('search'))
    pygal_config = pygal.Config()
    pygal_config.js = (settings.STATIC_URL + '/se/pygal-tooltips.min.js',)

    pygal_style = pygal.style.Style(
        background='transparent',
        plot_background='transparent',
        title_font_size=40,
        legend_font_size=30,
        label_font_size=30,
        major_label_font_size=30,
        value_font_size=30,
        value_label_font_size=30
    )

    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_database_size(%s)', [settings.DATABASES['default']['NAME']])
        db_size = cursor.fetchall()[0][0]

    doc_count = Document.objects.count()
    indexed_langs = Document.objects.exclude(lang_iso_639_1__isnull=True).values('lang_iso_639_1').annotate(count=models.Count('lang_iso_639_1')).order_by('-count')

    # Language chart
    lang_chart = None
    if indexed_langs:
        lang_chart = pygal.Bar(pygal_config, style=pygal_style, disable_xml_declaration=True, range=(0, None))
        lang_chart.title = "Document's language"

        factor, unit = get_unit(indexed_langs[0]['count'])
        if unit:
            lang_chart.title += ' (%s)' % unit

        for lang in indexed_langs[:8]:
            lang_iso = lang['lang_iso_639_1']
            lang_desc = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {})
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

    # Screenshot dir size
    # https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
    screenshot_size = 0
    for dirpath, dirnames, filenames in os.walk(settings.SOSSE_SCREENSHOTS_DIR):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                screenshot_size += os.path.getsize(fp)

    hdd_pie = pygal.Pie(pygal_config, style=pygal_style, disable_xml_declaration=True)
    hdd_pie.title = 'HDD size (total %s)' % filesizeformat(hdd_size)
    hdd_pie.add('DB(%s)' % filesizeformat(db_size), db_size)
    hdd_pie.add('Screenshots(%s)' % filesizeformat(screenshot_size), screenshot_size)
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
        'lang_parsable': [lang.title() for lang in sorted(Document.get_supported_langs())],
        'lang_chart': lang_chart,
        'hdd_pie': hdd_pie.render(),
    })

    context.update(crawler_stats(pygal_config, pygal_style, MINUTELY))
    context.update(crawler_stats(pygal_config, pygal_style, DAILY))
    return render(request, 'se/stats.html', context)
