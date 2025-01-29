| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot

| *Test Cases* |
| Monitor website
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import Link ; Link.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.document import Document ; Document.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.crawl_policy import CrawlPolicy ; CrawlPolicy.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../guide_feed_website_monitor.json | shell=True
|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | SOSSE Capture Page Screenshot | guide_feed_website_monitor_policies.png
|  | SOSSE Go To | http://127.0.0.1/?l\=fr&ps\=20&c\=1&o\=l&q\=&doc_lang\=&s\=-modified_date&ft1\=inc&ff1\=doc&fo1\=regexp&fv1\=%28Unavailable%7CGateway+Timeout%7CRequest+Timeout%29
# Increase the bottom padding of the top bar to make the Atom dropdown visible
|  | Execute Javascript | const top_bar = document.getElementById('top_bar')
|  | Execute Javascript | top_bar.style.paddingBottom = '45px'
|  | Click Element | id=atom_button
|  | Capture Element Screenshot | id=top_bar | guide_feed_website_monitor_error_search.png
