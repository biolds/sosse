# Copyright 2022-2024 Laurent Defert
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

from django.core.management import call_command
from django.test import TransactionTestCase

from .document import Document


class CommandsTest(TransactionTestCase):
    def setUp(self):
        Document.objects.create(url='http://test/')

    def test_delete_document_match(self):
        self.assertEqual(Document.objects.count(), 1)
        call_command('delete_documents', 'http://test')
        self.assertEqual(Document.objects.count(), 0)

    def test_delete_document_no_match(self):
        self.assertEqual(Document.objects.count(), 1)
        call_command('delete_documents', 'http://no_test')
        self.assertEqual(Document.objects.count(), 1)

    def test_delete_document_dry_run(self):
        self.assertEqual(Document.objects.count(), 1)
        with self.assertRaises(SystemExit):
            call_command('delete_documents', '--dry-run', 'http://test')
        self.assertEqual(Document.objects.count(), 1)
