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

from django.core.management import get_commands, load_command_class
from django.core.management.base import BaseCommand

from sosse.conf import DEFAULTS as DEFAULT_CONF


SECTIONS = [
    ['common', 'This section describes options common to the web interface and the crawlers.'],
    ['webserver', 'This section describes options dedicated to the web interface.'],
    ['crawler', 'This section describes options dedicated to the web interface.'],
]


class Command(BaseCommand):
    help = 'Displays code-defined documentation on stdout.'

    def add_arguments(self, parser):
        parser.add_argument('component', choices=['conf', 'cli'], help='"conf" for the configuration file,\n"cli" for the CLI')

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
                    comment = '\n'.join('   ' + line.strip() for line in comment.splitlines())
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
