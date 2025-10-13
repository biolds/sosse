| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Resource | ../tests/documents.robot

| *Test Cases* |
| Download
# Kill the crawler before starting
|  | ${ret}= | Run Process | pkill | sosse-admin
|  | Log | ${ret.stdout}
|  | Log | ${ret.stderr}
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import Link ; Link.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.document import Document ; Document.objects.wo_content().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.collection import Collection ; Collection.objects.all().delete()
|  | Load Data With Collection | ${CURDIR}/download_data/dump.json
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.document import Document ; from django.utils.timezone import now ; Document.objects.update(crawl_last\=now())
|  | Run Command | rm | -rf | /var/lib/sosse/html | /var/lib/sosse/screenshots
|  | Run Command | mkdir | -p | /var/lib/sosse/
|  | Run Command | cp | -r | ${CURDIR}/download_data/* | /var/lib/sosse/ | shell=True
|  | Run Command | dd | if\=/dev/zero | of\=/var/lib/sosse/html/https,3A/www.gutenberg.org/cache/epub/75210/pg75210-images-3.epub_b9a445dff6.epub | count\=5000
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | Sosse Capture Page Screenshot | guide_download_collections.png
|  | Sosse Go To | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Sosse Capture Page Screenshot | guide_download_crawl_queue.png
|  | Sosse Go To | http://127.0.0.1/?q\=&doc_lang\=&s\=-crawl_first&ft1\=inc&ff1\=lby_url&fo1\=equal&fv1\=https%3A%2F%2Fwww.gutenberg.org%2Fcache%2Fepub%2Ffeeds%2Ftoday.rss&l\=fr&ps\=20&c\=1
|  | Sosse Capture Page Screenshot | guide_download_view_library.png
|  | Sosse Go To | http://127.0.0.1/html/https://www.gutenberg.org/ebooks/75218
|  | Sosse Capture Page Screenshot | guide_download_archive_html.png
|  | Sosse Go To | http://127.0.0.1/download/https://www.gutenberg.org/cache/epub/75210/pg75210-images-3.epub
|  | Sosse Capture Page Screenshot | guide_download_archive_download.png
