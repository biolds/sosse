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

from argparse import ArgumentParser
import base64
import json
import os
import unicodedata

from django.conf import settings
from django.core.management import get_commands, load_command_class
from django.core.management.base import BaseCommand

from sosse.conf import DEFAULTS as DEFAULT_CONF
from .update_se import SE_FILE


SECTIONS = [
    ['common', 'This section describes options common to the web interface and the crawlers.'],
    ['webserver', 'This section describes options dedicated to the web interface.'],
    ['crawler', 'This section describes options dedicated to the web interface.'],
]


EXAMPLE_SEARCH_STR = 'SOSSE'


def unicode_len(s):
    _len = 0
    for c in s:
        _len += 1
        if unicodedata.name(c).startswith('CJK UNIFIED IDEOGRAPH'):
            _len += 1
    return _len


def unicode_justify(s, _len):
    return s + ' ' * (_len - unicode_len(s))


class Command(BaseCommand):
    help = 'Displays code-defined documentation on stdout.'

    def add_arguments(self, parser):
        parser.add_argument('component', choices=['conf', 'cli', 'se'], help='"conf" for the configuration file,\n"cli" for the CLI,\n"se" for search engines')

    def handle(self, *args, **options):
        if options['component'] == 'conf':
            for section, descr in SECTIONS:
                section_title = f'[{section}] section'
                print(section_title)
                print('-' * len(section_title))
                print()
                print(descr)
                print()
                for name, conf in DEFAULT_CONF[section].items():
                    print('.. _conf_option_%s:' % name)
                    print()
                    print('.. describe:: %s' % name)
                    print()
                    default = conf.get('default')
                    if default is None or default == '':
                        default = '<empty>'
                    print('   *Default: %s*' % default)
                    print()
                    comment = conf.get('doc') or conf.get('comment', '')
                    comment = '\n'.join('   ' + line for line in comment.splitlines())
                    comment = comment.replace('\n   See ', '\n\n   See ')
                    if comment:
                        print(comment)
                    print('.. raw:: html')
                    print()
                    print('   <br/>')
                    print()
        elif options['component'] == 'cli':
            has_content = False
            for cmd, mod in sorted(get_commands().items(), key=lambda x: x[0]):
                if mod != 'se':
                    continue
                has_content = True
                klass = load_command_class('se', cmd)
                parser = ArgumentParser()
                klass.add_arguments(parser)

                print('.. _cli_%s:' % cmd)
                print()
                print('.. describe:: %s:' % cmd)

                txt = getattr(klass, 'doc', klass.help)
                txt = [''] + [line[4:] if line.startswith(' ' * 4) else line for line in txt.splitlines()] + ['']
                txt = '\n   '.join(txt)
                print(txt)

                print('.. code-block:: text')
                print()
                usage = [''] + parser.format_help().splitlines()
                usage = '\n   '.join(usage)
                usage = usage.replace('sosse_admin.py', 'sosse-admin %s' % cmd)
                print(usage)

                print('.. raw:: html')
                print()
                print('   <br/>')
                print()
            if not has_content:
                raise Exception('Failed')
        elif options['component'] == 'se':
            se_file = os.path.join(settings.BASE_DIR, SE_FILE)
            with open(se_file) as f:
                search_engines = json.load(f)
            search_engines = [entry['fields'] for entry in search_engines]
            SE_STR = '**Search Engine**'
            SC_STR = '**Shortcut example**'
            se_len = unicode_len(SE_STR)
            sc_len = unicode_len(SC_STR) + 1
            for se in search_engines:
                name = se['long_name'] or se['short_name']
                se['name'] = name
                url = se['html_template']
                url = url.replace('{searchTerms}', EXAMPLE_SEARCH_STR.replace(' ', '%20'))
                url = url.replace('{searchTermsBase64}', base64.b64encode(EXAMPLE_SEARCH_STR.encode('utf-8')).decode('utf-8'))
                url = '`%s%s %s <%s>`_' % (settings.SOSSE_SEARCH_SHORTCUT_CHAR, se['shortcut'], EXAMPLE_SEARCH_STR, url)
                se['shortcut'] = url

                se_len = max(se_len, unicode_len(name))
                sc_len = max(sc_len, unicode_len(se['shortcut']))

            print('.. table::')
            print('   :align: left')
            print('   :widths: auto')
            print()
            print('   ' + '=' * se_len + '  ' + '=' * sc_len)
            print('   ' + SE_STR.ljust(se_len) + '  ' + SC_STR.ljust(sc_len))
            print('   ' + '=' * se_len + '  ' + '=' * sc_len)

            search_engines = sorted(search_engines, key=lambda x: x['name'])

            for se in search_engines:
                print('   ' + unicode_justify(se['name'], se_len) + '  ' + unicode_justify(se['shortcut'], sc_len))
            print('   ' + '=' * se_len + '  ' + '=' * sc_len)
            print()
            print()
