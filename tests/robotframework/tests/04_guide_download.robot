| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot

| *Test Cases* |
| Download
# Kill the crawler before starting
|  | ${ret}= | Run Process | pkill | sosse-admin
|  | Log | ${ret.stdout}
|  | Log | ${ret.stderr}
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import Link ; Link.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.document import Document ; Document.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.crawl_policy import CrawlPolicy ; CrawlPolicy.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../guide_download/guide_download_dump.json | shell=True
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.document import Document ; from django.utils.timezone import now ; Document.objects.update(crawl_last\=now())
|  | Run Command | rm | -rf | /var/lib/sosse/html | /var/lib/sosse/screenshots
|  | Run Command | mkdir | -p | /var/lib/sosse/
|  | Run Command | tar | -x | -C | /var/lib/sosse/ | -f | ${CURDIR}/../guide_download/guide_download_html.tar
|  | Run Command | dd | if\=/dev/zero | of\=/var/lib/sosse/html/https,3A/www.gutenberg.org/cache/epub/75210/pg75210-images-3.epub_b9a445dff6.epub | count\=5000
|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | SOSSE Capture Page Screenshot | guide_download_crawl_policies.png
|  | SOSSE Go To | http://127.0.0.1/admin/se/document/crawl_queue/
|  | SOSSE Capture Page Screenshot | guide_download_crawl_queue.png
|  | SOSSE Go To | http://127.0.0.1/?q\=&doc_lang\=&s\=-crawl_first&ft1\=inc&ff1\=lby_url&fo1\=equal&fv1\=https%3A%2F%2Fwww.gutenberg.org%2Fcache%2Fepub%2Ffeeds%2Ftoday.rss&l\=fr&ps\=20&c\=1
|  | SOSSE Capture Page Screenshot | guide_download_view_library.png
|  | SOSSE Go To | http://127.0.0.1/html/https://www.gutenberg.org/ebooks/75218
|  | SOSSE Capture Page Screenshot | guide_download_archive_html.png
|  | SOSSE Go To | http://127.0.0.1/download/https://www.gutenberg.org/cache/epub/75210/pg75210-images-3.epub
|  | SOSSE Capture Page Screenshot | guide_download_archive_download.png
