| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Resource | ../tests/documents.robot

| *Test Cases* |
| Monitor website
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import Link ; Link.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.document import Document ; Document.objects.wo_content().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.collection import Collection ; Collection.objects.all().delete()
|  | Load Data With Collection | ${CURDIR}/feed_monitor_data/dump.json
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | Sosse Capture Page Screenshot | guide_feed_website_monitor_collections.png
|  | Sosse Go To | http://127.0.0.1/?l\=fr&ps\=20&c\=1&o\=l&q\=&doc_lang\=&s\=-modified_date&ft1\=inc&ff1\=doc&fo1\=regexp&fv1\=%28Unavailable%7CGateway+Timeout%7CRequest+Timeout%29
# Increase the bottom padding of the top bar to make the Atom dropdown visible
|  | Execute Javascript | const top_bar = document.getElementById('top_bar')
|  | Execute Javascript | top_bar.style.paddingBottom = '45px'
|  | Click Element | id=atom_button
|  | Capture Element Screenshot | id=top_bar | guide_feed_website_monitor_error_search.png
