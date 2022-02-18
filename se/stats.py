import os

from django.db import connection, models
from django.conf import settings
from django.shortcuts import render
from langdetect.detector_factory import PROFILES_DIRECTORY
import pygal

from .models import Document
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


def stats(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_database_size(%s)', [settings.DATABASES['default']['NAME']])
        db_size = cursor.fetchall()[0][0]

    doc_count = Document.objects.count()

    indexed_langs = Document.objects.exclude(lang_iso_639_1__isnull=True).values('lang_iso_639_1').annotate(count=models.Count('lang_iso_639_1')).order_by('-count')

    # Language chart
    pygal_style = pygal.style.Style(
        background='transparent',
        plot_background='transparent',
        title_font_size=40,
        legend_font_size=40,
        label_font_size=40,
        major_label_font_size=40,
    )
    lang_chart = pygal.Bar(style=pygal_style, disable_xml_declaration=True)
    lang_chart.title = 'Language repartition'

    factor, unit = get_unit(indexed_langs[0]['count'])
    if unit:
        lang_chart.title += ' (%s)' % unit

    for lang in indexed_langs[:8]:
        lang_iso = lang['lang_iso_639_1']
        title = settings.MYSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get('name', 'unknown').title()
        percent = lang['count'] / factor
        lang_chart.add(title, percent)

    # HDD chart
    statvfs = os.statvfs('/var/lib')
    hdd_size = statvfs.f_frsize * statvfs.f_blocks
    hdd_free = statvfs.f_frsize * statvfs.f_bavail
    hdd_other = hdd_size - hdd_free - db_size
    factor, unit = get_unit(hdd_size)

    hdd_pie = pygal.Pie(style=pygal_style, disable_xml_declaration=True)
    hdd_pie.title = 'HDD size(%s)' % filesizeformat(hdd_size)
    hdd_pie.add('DB(%s)' % filesizeformat(db_size), db_size)
    hdd_pie.add('Other(%s)' % filesizeformat(hdd_other), hdd_other)
    hdd_pie.add('Free(%s)' % filesizeformat(hdd_free), hdd_free)

    context = get_context({
        'title': 'Statistics',

        # index
        'doc_count': doc_count,
        'lang_count': len(indexed_langs),
        'db_size': db_size,
        'doc_size': db_size / doc_count,
        'lang_recognizable': len(os.listdir(PROFILES_DIRECTORY)),
        'lang_parsable': [l.title() for l in sorted(Document.get_supported_langs())],
        'lang_chart': lang_chart.render(),
        'hdd_pie': hdd_pie.render()
    })

    return render(request, 'se/stats.html', context)

