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

import json
import sys

from se.document import Document

docs = []
for doc in Document.objects.w_content().all():
    # Serialize into json the document, using the same format as the django-admin dumpdata command
    docs.append(
        {
            "model": "se.document",
            "pk": doc.pk,
            "fields": {
                "url": doc.url,
                "title": doc.title,
                "content": doc.content,
                "mimetype": doc.mimetype,
                "modified_date": doc.modified_date.isoformat(),
                "crawl_first": doc.crawl_first.isoformat() if doc.crawl_first else None,
                "crawl_last": doc.crawl_last.isoformat() if doc.crawl_last else None,
                "crawl_next": doc.crawl_next.isoformat() if doc.crawl_next else None,
                "crawl_dt": str(doc.crawl_dt.total_seconds()) if doc.crawl_dt else None,
                "favicon": doc.favicon.pk if doc.favicon else None,
                "metadata": doc.metadata,
                "show_on_homepage": doc.show_on_homepage,
                "has_html_snapshot": doc.has_html_snapshot,
                "screenshot_count": doc.screenshot_count,
                "screenshot_format": doc.screenshot_format,
                "screenshot_size": doc.screenshot_size,
                "has_thumbnail": doc.has_thumbnail,
                "webhooks_result": doc.webhooks_result,
            },
        }
    )

sys.stdout.write(json.dumps(docs, indent=2, ensure_ascii=False))
sys.stdout.write("\n")
