# Copyright 2025 Laurent Defert
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

from django.test import TransactionTestCase

from .admin import DocumentOrphanFilter
from .document import Document
from .models import Link


class TestAdmin(TransactionTestCase):
    def test_document_orphan_filter(self):
        orphan = Document.objects.create(url="http://orphan")
        parent = Document.objects.create(url="http://parent")
        child = Document.objects.create(url="http://child")
        Link.objects.create(doc_from=parent, doc_to=child, pos=0, link_no=0)

        redirect_src = Document.objects.create(url="http://redirect_src", redirect_url="http://redirect_dst")
        redirect_dst = Document.objects.create(url="http://redirect_dst")

        doc_filter = DocumentOrphanFilter(None, {"orphan": "full"}, Document, None)
        orphaned = doc_filter.queryset(None, Document.objects.all())
        self.assertEqual(list(orphaned), [orphan])

        doc_filter = DocumentOrphanFilter(None, {"orphan": "no_parent"}, Document, None)
        orphaned = doc_filter.queryset(None, Document.objects.all())
        self.assertEqual(list(orphaned), [orphan, parent, redirect_src])

        doc_filter = DocumentOrphanFilter(None, {"orphan": "no_children"}, Document, None)
        orphaned = doc_filter.queryset(None, Document.objects.all())
        self.assertEqual(list(orphaned), [orphan, child, redirect_dst])
