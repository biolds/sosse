| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Resource | ../tests/documents.robot

| *Test Cases* |
| Authentication
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import Link ; Link.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.document import Document ; Document.objects.wo_content().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.collection import Collection ; Collection.objects.all().delete()
|  | Load Data With Collection | ${CURDIR}/auth_data/dump.json
|  | Run Command | rm | -rf | /var/lib/sosse/screenshots
|  | Run Command | mkdir | -p | /var/lib/sosse/
|  | Run Command | cp | -r | ${CURDIR}/auth_data/* | /var/lib/sosse/ | shell=True
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | Click Link | Calibre-Web
|  | Click Link | 🔒 Authentication
|  | Sosse Capture Page Screenshot | guide_authentication_auth.png
|  | Sosse Go To | http://127.0.0.1/?l\=fr&ps\=20&q\=Bernard+Werber&s\=crawl_first&ft1\=inc&ff1\=url&fo1\=contain&fv1\=http%3A%2F%2F192.168.119.11%3A8083%2Fbook%2F#
|  | Sosse Capture Page Screenshot | guide_authentication_search.png
