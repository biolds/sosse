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

from django.core.management.base import BaseCommand


from ...models import SearchEngine


class Command(BaseCommand):
    help = 'Loads a search engine definition from an OpenSearch Description formatted XML file.'
    doc = '''Loads a :doc:`user/shortcuts` from an `OpenSearch Description <https://developer.mozilla.org/en-US/docs/Web/OpenSearch>`_ formatted XML file.

    Most search engines provide such a file, defined in the HTML of their web page.
    It can be found inside a ``<link>`` element below the ``<head>`` tag, for example `Brave Search <https://search.brave.com/>`_ defines it as:

    .. code-block:: html

       <link rel="search" type="application/opensearchdescription+xml" title="Brave Search" href="https://cdn.search.brave.com/opensearch.xml">
    '''

    def add_arguments(self, parser):
        parser.add_argument('opensearch_file', nargs=1, type=str, help='OpenSearch Description formatted XML file.')

    def handle(self, *args, **options):
        SearchEngine.parse_xml_file(options['opensearch_file'][0])
