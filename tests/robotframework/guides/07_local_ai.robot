| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Resource | ../tests/documents.robot

| *Test Cases* |
| Local AI
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import Link ; Link.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import FavIcon ; FavIcon.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.document import Document ; Document.objects.wo_content().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.html_asset import HTMLAsset ; HTMLAsset.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.collection import Collection ; Collection.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.tag import Tag ; Tag.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.webhook import Webhook ; Webhook.objects.all().delete()
|  | Load Data With Collection | ${CURDIR}/local_ai/dump.json
|  | Run Command | rm | -rf | /var/lib/sosse/screenshots
|  | Run Command | mkdir | -p | /var/lib/sosse/
|  | Run Command | cp | -r | ${CURDIR}/local_ai/* | /var/lib/sosse/ | shell=True

|  | Sosse Go To | http://127.0.0.1/admin/se/webhook/
|  | Click Link | Summarize Article
|  | Execute JavaScript | document.getElementById('id_url').scrollIntoView({block: 'start'})
|  | Sosse Capture Page Screenshot | guide_local_ai_webhook_config.png

|  | Sosse Go To | http://127.0.0.1/
|  | Click Element | id=more
|  | Select From List By Label | id=id_s | First crawled descending
|  | Select From List By Label | xpath=//select[@name="ft1"] | Keep
|  | Select From List By Label | xpath=//select[@name="ff1"] | Linked by url
|  | Select From List By Label | xpath=//select[@name="fo1"] | Equal to
|  | Input Text | xpath=//input[@name="fv1"] | https://segment.com/blog/rss.xml
|  | Click Button | id=search_button
|  | Sosse Capture Page Screenshot | guide_local_ai_results.png
