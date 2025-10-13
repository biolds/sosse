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

import logging

from django.db import migrations

from se.utils import build_multiline_re

logger = logging.getLogger("django.db.migrations")


# Constants for old CrawlPolicy recursion values
CRAWL_ALL = "always"
CRAWL_ON_DEPTH = "depth"
CRAWL_NEVER = "never"


def create_default_policy(apps, schema_editor):
    Collection = apps.get_model("se", "Collection")
    Collection.objects.get_or_create(
        unlimited_regex="(default)",
        defaults={
            "name": "Default",
            "unlimited_regex": "(default)",
            "unlimited_regex_pg": ".*",
            "recursion": CRAWL_ON_DEPTH,
        },
    )[0]


def update_default_policy(apps, schema_editor):
    Collection = apps.get_model("se", "Collection")
    default_collection = Collection.objects.get(unlimited_regex="(default)")
    default_recursion = default_collection.recursion
    if default_recursion == CRAWL_NEVER:
        default_collection.unlimited_regex = ""
        default_collection.unlimited_regex_pg = ""
        default_collection.limited_regex = ""
        default_collection.limited_regex_pg = ""
    elif default_recursion == CRAWL_ALL:
        default_collection.unlimited_regex = ".*"
        default_collection.unlimited_regex_pg = ".*"
        default_collection.limited_regex = ""
        default_collection.limited_regex_pg = ""
    else:
        default_collection.unlimited_regex = ""
        default_collection.unlimited_regex_pg = ""
        default_collection.limited_regex = ".*"
        default_collection.limited_regex_pg = ".*"
    default_collection.save(
        update_fields=["unlimited_regex", "unlimited_regex_pg", "limited_regex", "limited_regex_pg"]
    )


def get_title_label(collection):
    """Get title label from collection's unlimited_regex."""

    def plural(count):
        return "s" if count > 1 else ""

    if collection.unlimited_regex == "(default)":
        return "Default"

    if collection.unlimited_regex:
        url_regexs = [line.strip() for line in collection.unlimited_regex.splitlines()]
        url_regexs = [line for line in url_regexs if not line.startswith("#") and line]
        if len(url_regexs) == 1:
            return f"{url_regexs[0]}"
        elif len(url_regexs) > 1:
            others = len(url_regexs) - 1
            others = f"{others} other{plural(others)}"
            return f"{url_regexs[0]} (and {others})"
    return "<empty>"


def get_unique_name(Collection, base_name):
    """Get a unique name by adding a counter if needed."""
    name = base_name
    counter = 2

    while Collection.objects.filter(name=name).exists():
        name = f"{base_name} {counter}"
        counter += 1

    return name


def populate_collection_names(apps, schema_editor):
    """Populate the name field for existing collections using get_title_label
    logic."""
    Collection = apps.get_model("se", "Collection")

    for collection in Collection.objects.exclude(name="Default"):
        base_name = get_title_label(collection)
        unique_name = get_unique_name(Collection, base_name)
        collection.name = unique_name
        collection.save(update_fields=["name"])


def transform_collection_data(apps, schema_editor):
    """Transform collections from old CrawlPolicy format to new Collection
    format."""
    Collection = apps.get_model("se", "Collection")

    # Get default collection and its recursion value
    default_collection = Collection.objects.get(unlimited_regex="(default)")
    default_recursion = default_collection.recursion

    transformed = 0
    for collection in Collection.objects.exclude(id=default_collection.id).iterator():
        enabled = collection.enabled
        recursion = collection.recursion

        logger.debug(f"Processing collection {collection.id}: enabled={enabled}, recursion={recursion}")

        # Store original url_regex (now unlimited_regex)
        original_regex = collection.unlimited_regex

        # If disabled, clear all regex fields
        if not enabled:
            collection.unlimited_regex = ""
            collection.unlimited_regex_pg = ""
            collection.limited_regex = ""
            collection.limited_regex_pg = ""
            collection.save(
                update_fields=["unlimited_regex", "unlimited_regex_pg", "limited_regex", "limited_regex_pg"]
            )
            transformed += 1
            continue

        # Transform based on default collection's recursion and this collection's recursion
        if default_recursion == CRAWL_NEVER:
            if recursion == CRAWL_ALL:
                collection.unlimited_regex = original_regex
                collection.unlimited_regex_pg = build_multiline_re(original_regex)
                collection.limited_regex = ""
                collection.limited_regex_pg = ""
            elif recursion == CRAWL_ON_DEPTH:
                collection.unlimited_regex = ""
                collection.unlimited_regex_pg = ""
                collection.limited_regex = original_regex
                collection.limited_regex_pg = build_multiline_re(original_regex)
            elif recursion == CRAWL_NEVER:
                collection.unlimited_regex = ""
                collection.unlimited_regex_pg = ""
                collection.limited_regex = ""
                collection.limited_regex_pg = ""

        elif default_recursion == CRAWL_ON_DEPTH:
            if recursion == CRAWL_ALL:
                collection.unlimited_regex = original_regex
                collection.unlimited_regex_pg = build_multiline_re(original_regex)
                collection.limited_regex = ".*"
                collection.limited_regex_pg = ".*"
            elif recursion == CRAWL_ON_DEPTH:
                collection.unlimited_regex = ""
                collection.unlimited_regex_pg = ""
                collection.limited_regex = original_regex
                collection.limited_regex_pg = build_multiline_re(original_regex)
            elif recursion == CRAWL_NEVER:
                collection.unlimited_regex = ""
                collection.unlimited_regex_pg = ""
                collection.limited_regex = ""
                collection.limited_regex_pg = ""

        elif default_recursion == CRAWL_ALL:
            if recursion == CRAWL_ALL:
                collection.unlimited_regex = original_regex
                collection.unlimited_regex_pg = build_multiline_re(original_regex)
                collection.limited_regex = ""
                collection.limited_regex_pg = ""
            elif recursion == CRAWL_ON_DEPTH:
                collection.unlimited_regex = ""
                collection.unlimited_regex_pg = ""
                collection.limited_regex = original_regex
                collection.limited_regex_pg = build_multiline_re(original_regex)
            elif recursion == CRAWL_NEVER:
                collection.unlimited_regex = ""
                collection.unlimited_regex_pg = ""
                collection.limited_regex = ""
                collection.limited_regex_pg = ""

        collection.save(update_fields=["unlimited_regex", "unlimited_regex_pg", "limited_regex", "limited_regex_pg"])
        transformed += 1

    logger.info(f"Collection transformation completed: {transformed} collections transformed")


def populate_document_collections(apps, schema_editor):
    """Populate the collection field for existing documents using
    Collection.get_from_url()"""
    Document = apps.get_model("se", "Document")
    Collection = apps.get_model("se", "Collection")

    # Recreate the get_from_url logic using SQL operations like the production version
    def get_collection_from_url(url):
        from django.db import models

        # Get all collections except default, excluding empty regex
        queryset = Collection.objects.exclude(unlimited_regex="(default)")
        queryset = queryset.exclude(unlimited_regex_pg="")

        # Use PostgreSQL REGEXP_SUBSTR to find the best match
        return (
            queryset.annotate(
                match_len=models.functions.Length(
                    models.Func(
                        models.Value(url),
                        models.F("unlimited_regex_pg"),
                        function="REGEXP_SUBSTR",
                        output_field=models.TextField(),
                    )
                )
            )
            .filter(match_len__gt=0)
            .order_by("-match_len")
            .first()
        )

    # Process all documents
    total_docs = Document.objects.count()
    processed = 0

    logger.info(f"\nStarting document collection assignment: processing {total_docs} documents...")

    default_collection = Collection.objects.get(unlimited_regex="(default)")
    for document in Document.objects.iterator():
        collection = get_collection_from_url(document.url)
        if collection is None:
            collection = default_collection
        document.collection = collection
        document.save(update_fields=["collection"])
        processed += 1

        if processed % 1000 == 0:
            logger.info(f"Processed {processed}/{total_docs} documents...")

    logger.info(f"Document collection assignment completed: {processed} documents processed")


def populate_combined_regex_pg(apps, schema_editor):
    """Populate the combined_regex_pg field for all existing collections."""
    Collection = apps.get_model("se", "Collection")

    for collection in Collection.objects.all():
        # Build combined regex for cross-collection matching
        unlimited_regex_pg = collection.unlimited_regex_pg or ""
        limited_regex_pg = collection.limited_regex_pg or ""

        if unlimited_regex_pg and limited_regex_pg:
            collection.combined_regex_pg = f"{unlimited_regex_pg}|{limited_regex_pg}"
        elif unlimited_regex_pg:
            collection.combined_regex_pg = unlimited_regex_pg
        elif limited_regex_pg:
            collection.combined_regex_pg = limited_regex_pg
        else:
            collection.combined_regex_pg = ""

        collection.save(update_fields=["combined_regex_pg"])


class Migration(migrations.Migration):
    dependencies = [
        ("se", "0020_collection"),
    ]

    operations = [
        migrations.RunPython(create_default_policy, migrations.RunPython.noop),
        migrations.RunPython(populate_collection_names, migrations.RunPython.noop),
        migrations.RunPython(populate_document_collections, migrations.RunPython.noop),
        migrations.RunPython(transform_collection_data, migrations.RunPython.noop),
        migrations.RunPython(update_default_policy, migrations.RunPython.noop),
        migrations.RunPython(populate_combined_regex_pg, migrations.RunPython.noop),
    ]
