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

from unittest import TestCase

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

# Constants for old CrawlPolicy recursion values
CRAWL_ALL = "always"
CRAWL_ON_DEPTH = "depth"
CRAWL_NEVER = "never"


def migrate_to_state(app_label, migration_name):
    """Apply migration physically and return apps state."""
    call_command("migrate", app_label, migration_name, verbosity=0)
    executor = MigrationExecutor(connection)
    return executor.loader.project_state([(app_label, migration_name)]).apps


class MigrationExecutorTest(TestCase):
    @staticmethod
    def _clear_tables():
        with connection.cursor() as cursor:
            # Check if tables exist before truncating
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name IN
                ('se_document', 'se_crawlpolicy_tags', 'se_crawlpolicy_webhooks', 'se_crawlpolicy', 'se_authfield', 'se_tag', 'se_webhook')
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]

            if existing_tables:
                tables_list = ", ".join(existing_tables)
                cursor.execute(f"TRUNCATE TABLE {tables_list} CASCADE")

    def setUp(self):
        MigrationExecutorTest._clear_tables()

    @classmethod
    def tearDownClass(cls):
        """Reapply all migrations and clean data after all tests."""
        super().tearDownClass()
        call_command("migrate", "se", verbosity=0)
        MigrationExecutorTest._clear_tables()

    def _test_migration_scenario(
        self,
        default_recursion,
        specific_url,
        specific_recursion,
        expected_default_unlimited,
        expected_default_limited,
        expected_specific_unlimited,
        expected_specific_limited,
    ):
        """Helper method to test migration scenarios with different recursion
        types."""
        # Migrate to state before Collection exists
        apps = migrate_to_state("se", "0016_sosse_1_13_0_pre")
        CrawlPolicy = apps.get_model("se", "CrawlPolicy")

        # Since Django applies all migrations before the tests, we first clear all Crawl Policy to set a clean state
        CrawlPolicy.objects.all().delete()
        default_policy = CrawlPolicy.objects.create(
            url_regex="(default)", url_regex_pg=".*", recursion=default_recursion
        )
        CrawlPolicy.objects.create(url_regex=specific_url, url_regex_pg=specific_url, recursion=specific_recursion)
        Document = apps.get_model("se", "Document")
        Document.objects.create(url="http://default.com/")
        Document.objects.create(url=f"{specific_url}doc")

        # Migrate to final state with Collection
        apps = migrate_to_state("se", "0022_make_collection_non_null")
        Collection = apps.get_model("se", "Collection")
        Document = apps.get_model("se", "Document")

        # Should have 2 collections: Default and the specific one
        self.assertEqual(
            Collection.objects.count(), 2, Collection.objects.values("name", "unlimited_regex", "limited_regex")
        )

        # Check default collection
        default_collection = Collection.objects.get(name="Default")
        self.assertEqual(default_collection.unlimited_regex, expected_default_unlimited)
        self.assertEqual(default_collection.unlimited_regex_pg, expected_default_unlimited)
        self.assertEqual(default_collection.limited_regex, expected_default_limited)
        self.assertEqual(default_collection.limited_regex_pg, expected_default_limited)

        # Check specific collection
        specific_collection = Collection.objects.get(name=specific_url)
        self.assertEqual(specific_collection.unlimited_regex, expected_specific_unlimited)
        self.assertEqual(specific_collection.unlimited_regex_pg, expected_specific_unlimited)
        self.assertEqual(specific_collection.limited_regex, expected_specific_limited)
        self.assertEqual(specific_collection.limited_regex_pg, expected_specific_limited)

        # Check documents are assigned to correct collections
        default_doc = Document.objects.get(url="http://default.com/")
        specific_doc = Document.objects.get(url=f"{specific_url}doc")
        self.assertEqual(default_doc.collection, default_collection)
        self.assertEqual(specific_doc.collection, specific_collection)

        # Migrate back to initial state
        apps = migrate_to_state("se", "0016_sosse_1_13_0_pre")
        CrawlPolicy = apps.get_model("se", "CrawlPolicy")
        self.assertEqual(CrawlPolicy.objects.count(), 2, CrawlPolicy.objects.values())

        # Check default policy was restored
        default_policy = CrawlPolicy.objects.get(url_regex="(default)")
        self.assertEqual(default_policy.url_regex, "(default)")
        self.assertEqual(default_policy.url_regex_pg, ".*")
        self.assertEqual(default_policy.recursion, default_recursion)

        # Check specific policy was restored
        specific_policy = CrawlPolicy.objects.get(url_regex=specific_url)
        self.assertEqual(specific_policy.url_regex, specific_url)
        self.assertEqual(specific_policy.url_regex_pg, specific_url)
        self.assertEqual(specific_policy.recursion, specific_recursion)

    def test_010_simple_migration(self):
        # Migrate to state before Collection exists
        apps = migrate_to_state("se", "0016_sosse_1_13_0_pre")
        CrawlPolicy = apps.get_model("se", "CrawlPolicy")

        # Since Django applies all migrations before the tests, we first clear all Crawl Policy to set a clean state
        CrawlPolicy.objects.all().delete()
        CrawlPolicy.objects.create(url_regex="(default)", url_regex_pg=".*", recursion=CRAWL_ALL)

        # Migrate to final state with Collection
        apps = migrate_to_state("se", "0022_make_collection_non_null")
        Collection = apps.get_model("se", "Collection")
        self.assertEqual(
            Collection.objects.count(), 1, Collection.objects.values("name", "unlimited_regex", "unlimited_regex_pg")
        )
        collection = Collection.objects.first()
        self.assertEqual(collection.unlimited_regex, ".*")
        self.assertEqual(collection.unlimited_regex_pg, ".*")
        self.assertEqual(collection.limited_regex, "")
        self.assertEqual(collection.limited_regex_pg, "")

        # Migrate back to initial state
        apps = migrate_to_state("se", "0016_sosse_1_13_0_pre")
        CrawlPolicy = apps.get_model("se", "CrawlPolicy")
        self.assertEqual(CrawlPolicy.objects.count(), 1, CrawlPolicy.objects.values())
        crawl_policy = CrawlPolicy.objects.first()
        self.assertEqual(crawl_policy.url_regex, "(default)")
        self.assertEqual(crawl_policy.url_regex_pg, ".*")
        self.assertEqual(crawl_policy.recursion, CRAWL_ALL)

    def test_020_default_never_policy_all(self):
        self._test_migration_scenario(CRAWL_NEVER, "http://test.com/", CRAWL_ALL, "", "", "http://test.com/", "")

    def test_030_default_never_policy_depth(self):
        self._test_migration_scenario(CRAWL_NEVER, "http://depth.com/", CRAWL_ON_DEPTH, "", "", "", "http://depth.com/")

    def test_040_default_depth_policy_all(self):
        self._test_migration_scenario(CRAWL_ON_DEPTH, "http://test.com/", CRAWL_ALL, "", ".*", "http://test.com/", ".*")

    def test_050_default_depth_policy_depth(self):
        self._test_migration_scenario(
            CRAWL_ON_DEPTH, "http://depth.com/", CRAWL_ON_DEPTH, "", ".*", "", "http://depth.com/"
        )

    def test_060_default_depth_policy_never(self):
        self._test_migration_scenario(CRAWL_ON_DEPTH, "http://never.com/", CRAWL_NEVER, "", ".*", "", "")

    def test_070_default_all_policy_all(self):
        self._test_migration_scenario(CRAWL_ALL, "http://test.com/", CRAWL_ALL, ".*", "", "http://test.com/", "")

    def test_080_default_all_policy_depth(self):
        self._test_migration_scenario(CRAWL_ALL, "http://depth.com/", CRAWL_ON_DEPTH, ".*", "", "", "http://depth.com/")

    def test_090_default_all_policy_never(self):
        self._test_migration_scenario(CRAWL_ALL, "http://never.com/", CRAWL_NEVER, ".*", "", "", "")

    def test_100_tags_migration(self):
        # Migrate to state before Collection exists
        apps = migrate_to_state("se", "0016_sosse_1_13_0_pre")
        CrawlPolicy = apps.get_model("se", "CrawlPolicy")
        Tag = apps.get_model("se", "Tag")
        Document = apps.get_model("se", "Document")

        # Create test data
        CrawlPolicy.objects.all().delete()
        Tag.objects.all().delete()
        Document.objects.all().delete()

        tag1 = Tag.objects.create(name="tag1", depth=0, path="0001")
        tag2 = Tag.objects.create(name="tag2", depth=0, path="0002")

        default_policy = CrawlPolicy.objects.create(url_regex="(default)", url_regex_pg=".*", recursion=CRAWL_ALL)
        specific_policy = CrawlPolicy.objects.create(
            url_regex="http://test.com/", url_regex_pg="http://test.com/", recursion=CRAWL_ALL
        )

        default_policy.tags.set([tag1])
        specific_policy.tags.set([tag1, tag2])

        # Create documents and associate tags
        doc1 = Document.objects.create(url="http://default.com/")
        doc2 = Document.objects.create(url="http://test.com/doc")

        doc1.tags.set([tag1])
        doc2.tags.set([tag1, tag2])

        # Migrate to final state with Collection
        apps = migrate_to_state("se", "0022_make_collection_non_null")
        Collection = apps.get_model("se", "Collection")
        Document = apps.get_model("se", "Document")

        # Check tags are preserved on collections
        default_collection = Collection.objects.get(name="Default")
        specific_collection = Collection.objects.get(name="http://test.com/")

        self.assertEqual(list(default_collection.tags.values_list("name", flat=True)), ["tag1"])
        self.assertEqual(set(specific_collection.tags.values_list("name", flat=True)), {"tag1", "tag2"})

        # Check tags are preserved on documents
        doc1 = Document.objects.get(url="http://default.com/")
        doc2 = Document.objects.get(url="http://test.com/doc")

        self.assertEqual(list(doc1.tags.values_list("name", flat=True)), ["tag1"])
        self.assertEqual(set(doc2.tags.values_list("name", flat=True)), {"tag1", "tag2"})

        # Migrate back to initial state
        apps = migrate_to_state("se", "0016_sosse_1_13_0_pre")
        CrawlPolicy = apps.get_model("se", "CrawlPolicy")
        Document = apps.get_model("se", "Document")

        # Check tags are restored on policies
        default_policy = CrawlPolicy.objects.get(url_regex="(default)")
        specific_policy = CrawlPolicy.objects.get(url_regex="http://test.com/")

        self.assertEqual(list(default_policy.tags.values_list("name", flat=True)), ["tag1"])
        self.assertEqual(set(specific_policy.tags.values_list("name", flat=True)), {"tag1", "tag2"})

        # Check tags are still on documents
        doc1 = Document.objects.get(url="http://default.com/")
        doc2 = Document.objects.get(url="http://test.com/doc")

        self.assertEqual(list(doc1.tags.values_list("name", flat=True)), ["tag1"])
        self.assertEqual(set(doc2.tags.values_list("name", flat=True)), {"tag1", "tag2"})

    def test_110_webhooks_migration(self):
        # Migrate to state before Collection exists
        apps = migrate_to_state("se", "0016_sosse_1_13_0_pre")
        CrawlPolicy = apps.get_model("se", "CrawlPolicy")
        Webhook = apps.get_model("se", "Webhook")

        # Create test data
        CrawlPolicy.objects.all().delete()
        Webhook.objects.all().delete()

        webhook1 = Webhook.objects.create(name="webhook1", url="http://hook1.com")
        webhook2 = Webhook.objects.create(name="webhook2", url="http://hook2.com")

        default_policy = CrawlPolicy.objects.create(url_regex="(default)", url_regex_pg=".*", recursion=CRAWL_ALL)
        specific_policy = CrawlPolicy.objects.create(
            url_regex="http://test.com/", url_regex_pg="http://test.com/", recursion=CRAWL_ALL
        )

        default_policy.webhooks.set([webhook1])
        specific_policy.webhooks.set([webhook1, webhook2])

        # Migrate to final state with Collection
        apps = migrate_to_state("se", "0022_make_collection_non_null")
        Collection = apps.get_model("se", "Collection")
        Webhook = apps.get_model("se", "Webhook")

        # Check webhooks are preserved
        default_collection = Collection.objects.get(name="Default")
        specific_collection = Collection.objects.get(name="http://test.com/")

        self.assertEqual(list(default_collection.webhooks.values_list("name", flat=True)), ["webhook1"])
        self.assertEqual(set(specific_collection.webhooks.values_list("name", flat=True)), {"webhook1", "webhook2"})

        # Migrate back to initial state
        apps = migrate_to_state("se", "0016_sosse_1_13_0_pre")
        CrawlPolicy = apps.get_model("se", "CrawlPolicy")
        Webhook = apps.get_model("se", "Webhook")

        # Check webhooks are restored
        default_policy = CrawlPolicy.objects.get(url_regex="(default)")
        specific_policy = CrawlPolicy.objects.get(url_regex="http://test.com/")

        self.assertEqual(list(default_policy.webhooks.values_list("name", flat=True)), ["webhook1"])
        self.assertEqual(set(specific_policy.webhooks.values_list("name", flat=True)), {"webhook1", "webhook2"})

    def test_120_authfields_migration(self):
        # Migrate to state before Collection exists
        apps = migrate_to_state("se", "0016_sosse_1_13_0_pre")
        CrawlPolicy = apps.get_model("se", "CrawlPolicy")
        AuthField = apps.get_model("se", "AuthField")

        # Create test data
        CrawlPolicy.objects.all().delete()
        AuthField.objects.all().delete()

        default_policy = CrawlPolicy.objects.create(url_regex="(default)", url_regex_pg=".*", recursion=CRAWL_ALL)
        specific_policy = CrawlPolicy.objects.create(
            url_regex="http://test.com/", url_regex_pg="http://test.com/", recursion=CRAWL_ALL
        )

        AuthField.objects.create(key="username", value="admin", crawl_policy=default_policy)
        AuthField.objects.create(key="password", value="secret", crawl_policy=specific_policy)
        AuthField.objects.create(key="token", value="abc123", crawl_policy=specific_policy)

        # Migrate to final state with Collection
        apps = migrate_to_state("se", "0022_make_collection_non_null")
        Collection = apps.get_model("se", "Collection")
        AuthField = apps.get_model("se", "AuthField")

        # Check auth fields are preserved
        default_collection = Collection.objects.get(name="Default")
        specific_collection = Collection.objects.get(name="http://test.com/")

        default_auths = list(default_collection.authfield_set.values("key", "value"))
        specific_auths = list(specific_collection.authfield_set.values("key", "value"))

        self.assertEqual(default_auths, [{"key": "username", "value": "admin"}])
        self.assertEqual(len(specific_auths), 2)
        self.assertIn({"key": "password", "value": "secret"}, specific_auths)
        self.assertIn({"key": "token", "value": "abc123"}, specific_auths)

        # Migrate back to initial state
        apps = migrate_to_state("se", "0016_sosse_1_13_0_pre")
        CrawlPolicy = apps.get_model("se", "CrawlPolicy")
        AuthField = apps.get_model("se", "AuthField")

        # Check auth fields are restored
        default_policy = CrawlPolicy.objects.get(url_regex="(default)")
        specific_policy = CrawlPolicy.objects.get(url_regex="http://test.com/")

        default_auths = list(default_policy.authfield_set.values("key", "value"))
        specific_auths = list(specific_policy.authfield_set.values("key", "value"))

        self.assertEqual(default_auths, [{"key": "username", "value": "admin"}])
        self.assertEqual(len(specific_auths), 2)
        self.assertIn({"key": "password", "value": "secret"}, specific_auths)
        self.assertIn({"key": "token", "value": "abc123"}, specific_auths)
