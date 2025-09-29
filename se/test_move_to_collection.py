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

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from .collection import Collection
from .document import Document
from .move_to_collection import MoveToCollectionForm


class MoveToCollectionFormTest(TestCase):
    def setUp(self):
        self.collection1 = Collection.objects.create(name="Source Collection", unlimited_regex="http://source.com/.*")
        self.collection2 = Collection.objects.create(
            name="Destination Collection", unlimited_regex="http://dest.com/.*"
        )

    def test_form_fields(self):
        """Test that form has required fields with correct choices."""
        form = MoveToCollectionForm()

        # Test collection field
        self.assertIn("collection", form.fields)
        self.assertTrue(form.fields["collection"].required)

        # Test conflict_resolution field
        self.assertIn("conflict_resolution", form.fields)
        self.assertTrue(form.fields["conflict_resolution"].required)
        self.assertEqual(form.fields["conflict_resolution"].initial, MoveToCollectionForm.CONFLICT_OVERWRITE)

        # Test conflict choices
        expected_choices = [
            (MoveToCollectionForm.CONFLICT_SKIP, "Skip conflicting documents"),
            (MoveToCollectionForm.CONFLICT_OVERWRITE, "Overwrite documents in destination collection"),
            (MoveToCollectionForm.CONFLICT_DELETE_SOURCE, "Delete source document"),
        ]
        self.assertEqual(form.fields["conflict_resolution"].choices, expected_choices)

    def test_form_validation(self):
        """Test form validation with different inputs."""
        # Valid data
        form_data = {
            "collection": self.collection2.id,
            "conflict_resolution": MoveToCollectionForm.CONFLICT_OVERWRITE,
        }
        form = MoveToCollectionForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Invalid conflict resolution
        form_data["conflict_resolution"] = "invalid_choice"
        form = MoveToCollectionForm(data=form_data)
        self.assertFalse(form.is_valid())

        # Missing collection
        form_data = {
            "conflict_resolution": MoveToCollectionForm.CONFLICT_SKIP,
        }
        form = MoveToCollectionForm(data=form_data)
        self.assertFalse(form.is_valid())


class MoveToCollectionViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@example.com", "password")
        self.collection1 = Collection.objects.create(name="Source Collection", unlimited_regex="http://source.com/.*")
        self.collection2 = Collection.objects.create(
            name="Destination Collection", unlimited_regex="http://dest.com/.*"
        )

        # Create test documents
        self.doc1 = Document.objects.create(
            url="http://example.com/page1",
            title="Document 1",
            content="Content 1",
            collection=self.collection1,
        )
        self.doc2 = Document.objects.create(
            url="http://example.com/page2",
            title="Document 2",
            content="Content 2",
            collection=self.collection1,
        )
        # Document with same URL in destination collection (conflict)
        self.doc_conflict = Document.objects.create(
            url="http://example.com/page1",
            title="Conflicting Document",
            content="Conflicting Content",
            collection=self.collection2,
        )

    def test_skip_conflicts(self):
        """Test skipping conflicting documents."""
        self.client.login(username="admin", password="password")

        # Set up session with documents to move
        session = self.client.session
        session["documents_to_move"] = [self.doc1.id, self.doc2.id]
        session.save()

        # Submit form with SKIP option
        response = self.client.post(
            reverse("admin:move_to_collection"),
            {
                "collection": self.collection2.id,
                "conflict_resolution": MoveToCollectionForm.CONFLICT_SKIP,
            },
        )

        # Check redirect
        self.assertEqual(response.status_code, 302)

        # Check that doc1 was not moved (conflict), doc2 was moved
        self.doc1.refresh_from_db()
        self.doc2.refresh_from_db()

        self.assertEqual(self.doc1.collection, self.collection1)  # Not moved
        self.assertEqual(self.doc2.collection, self.collection2)  # Moved

        # Check that conflicting document still exists
        self.assertTrue(Document.objects.wo_content().filter(id=self.doc_conflict.id).exists())

    def test_overwrite_conflicts(self):
        """Test overwriting conflicting documents."""
        self.client.login(username="admin", password="password")

        # Set up session with documents to move
        session = self.client.session
        session["documents_to_move"] = [self.doc1.id, self.doc2.id]
        session.save()

        # Submit form with OVERWRITE option
        response = self.client.post(
            reverse("admin:move_to_collection"),
            {
                "collection": self.collection2.id,
                "conflict_resolution": MoveToCollectionForm.CONFLICT_OVERWRITE,
            },
        )

        # Check redirect
        self.assertEqual(response.status_code, 302)

        # Check that both documents were moved
        self.doc1.refresh_from_db()
        self.doc2.refresh_from_db()

        self.assertEqual(self.doc1.collection, self.collection2)
        self.assertEqual(self.doc2.collection, self.collection2)

        # Check that conflicting document was deleted
        self.assertFalse(Document.objects.wo_content().filter(id=self.doc_conflict.id).exists())

    def test_delete_source_conflicts(self):
        """Test deleting source documents on conflict."""
        self.client.login(username="admin", password="password")

        # Set up session with documents to move
        session = self.client.session
        session["documents_to_move"] = [self.doc1.id, self.doc2.id]
        session.save()

        # Submit form with DELETE_SOURCE option
        response = self.client.post(
            reverse("admin:move_to_collection"),
            {
                "collection": self.collection2.id,
                "conflict_resolution": MoveToCollectionForm.CONFLICT_DELETE_SOURCE,
            },
        )

        # Check redirect
        self.assertEqual(response.status_code, 302)

        # Check that doc1 was deleted (conflict), doc2 was moved
        self.assertFalse(Document.objects.wo_content().filter(id=self.doc1.id).exists())  # Deleted

        self.doc2.refresh_from_db()
        self.assertEqual(self.doc2.collection, self.collection2)  # Moved

        # Check that conflicting document still exists
        self.assertTrue(Document.objects.wo_content().filter(id=self.doc_conflict.id).exists())

    def test_no_conflicts(self):
        """Test moving documents without conflicts."""
        self.client.login(username="admin", password="password")

        # Remove the conflicting document
        self.doc_conflict.delete()

        # Set up session with documents to move
        session = self.client.session
        session["documents_to_move"] = [self.doc1.id, self.doc2.id]
        session.save()

        # Submit form
        response = self.client.post(
            reverse("admin:move_to_collection"),
            {
                "collection": self.collection2.id,
                "conflict_resolution": MoveToCollectionForm.CONFLICT_OVERWRITE,
            },
        )

        # Check redirect
        self.assertEqual(response.status_code, 302)

        # Check that both documents were moved
        self.doc1.refresh_from_db()
        self.doc2.refresh_from_db()

        self.assertEqual(self.doc1.collection, self.collection2)
        self.assertEqual(self.doc2.collection, self.collection2)

    def test_no_documents_selected(self):
        """Test behavior when no documents are selected."""
        self.client.login(username="admin", password="password")

        # Submit form without setting documents_to_move in session
        response = self.client.post(
            reverse("admin:move_to_collection"),
            {
                "collection": self.collection2.id,
                "conflict_resolution": MoveToCollectionForm.CONFLICT_OVERWRITE,
            },
        )

        # Check redirect
        self.assertEqual(response.status_code, 302)

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("No documents selected" in str(message) for message in messages))

    def test_get_view_without_documents(self):
        """Test GET request without documents in session."""
        self.client.login(username="admin", password="password")

        response = self.client.get(reverse("admin:move_to_collection"))

        # Should redirect with error message
        self.assertEqual(response.status_code, 302)

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("No documents selected" in str(message) for message in messages))

    def test_same_collection_as_destination(self):
        """Test moving documents to the same collection they are already in."""
        self.client.login(username="admin", password="password")

        # Set up session with documents to move to their current collection
        session = self.client.session
        session["documents_to_move"] = [self.doc1.id, self.doc2.id]
        session.save()

        # Submit form with same collection as source (collection1)
        response = self.client.post(
            reverse("admin:move_to_collection"),
            {
                "collection": self.collection1.id,  # Same as current collection
                "conflict_resolution": MoveToCollectionForm.CONFLICT_OVERWRITE,
            },
        )

        # Check redirect
        self.assertEqual(response.status_code, 302)

        # Check that documents remained in their original collection
        self.doc1.refresh_from_db()
        self.doc2.refresh_from_db()

        self.assertEqual(self.doc1.collection, self.collection1)
        self.assertEqual(self.doc2.collection, self.collection1)

    def test_get_view_with_documents(self):
        """Test GET request with documents in session."""
        self.client.login(username="admin", password="password")

        # Set up session with documents to move
        session = self.client.session
        session["documents_to_move"] = [self.doc1.id, self.doc2.id]
        session.save()

        response = self.client.get(reverse("admin:move_to_collection"))

        # Should display the form
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Move 2 documents to collection")
        self.assertContains(response, self.doc1.title)
        self.assertContains(response, self.doc2.title)
