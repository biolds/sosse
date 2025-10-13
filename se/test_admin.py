# Copyright 2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

from django.test import TransactionTestCase

from .admin import DocumentOrphanFilter
from .collection import Collection
from .document import Document
from .models import Link


class TestAdmin(TransactionTestCase):
    def setUp(self):
        self.collection = Collection.create_default()

    def test_document_orphan_filter(self):
        orphan = Document.objects.wo_content().create(url="http://orphan", collection=self.collection)
        parent = Document.objects.wo_content().create(url="http://parent", collection=self.collection)
        child = Document.objects.wo_content().create(url="http://child", collection=self.collection)
        Link.objects.create(doc_from=parent, doc_to=child, pos=0, link_no=0)

        redirect_src = Document.objects.wo_content().create(
            url="http://redirect_src", redirect_url="http://redirect_dst", collection=self.collection
        )
        redirect_dst = Document.objects.wo_content().create(url="http://redirect_dst", collection=self.collection)

        doc_filter = DocumentOrphanFilter(None, {"orphan": "full"}, Document, None)
        orphaned = doc_filter.queryset(None, Document.objects.wo_content().all())
        self.assertEqual(list(orphaned), [orphan])

        doc_filter = DocumentOrphanFilter(None, {"orphan": "no_parent"}, Document, None)
        orphaned = doc_filter.queryset(None, Document.objects.wo_content().all())
        self.assertEqual(list(orphaned), [orphan, parent, redirect_src])

        doc_filter = DocumentOrphanFilter(None, {"orphan": "no_children"}, Document, None)
        orphaned = doc_filter.queryset(None, Document.objects.wo_content().all())
        self.assertEqual(list(orphaned), [orphan, child, redirect_dst])
