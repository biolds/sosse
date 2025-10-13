| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Resource | ../tests/documents.robot

| *Test Cases* |
| AI API processing
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import Link ; Link.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.document import Document ; Document.objects.wo_content().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.html_asset import HTMLAsset ; HTMLAsset.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.collection import Collection ; Collection.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.tag import Tag ; Tag.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.webhook import Webhook ; Webhook.objects.all().delete()
|  | Load Data With Collection | ${CURDIR}/ai_api_processing/dump.json
|  | Run Command | rm | -rf | /var/lib/sosse/screenshots
|  | Run Command | mkdir | -p | /var/lib/sosse/
|  | Run Command | cp | -r | ${CURDIR}/ai_api_processing/* | /var/lib/sosse/ | shell=True

|  | Sosse Go To | http://127.0.0.1/admin/se/webhook/
|  | Click Link | Generate Tags
|  | Execute JavaScript | document.getElementById('id_url').scrollIntoView({block: 'start'})
|  | Sosse Capture Page Screenshot | guide_ai_api_webhook.png

|  | Sosse Go To | http://127.0.0.1/?ft1\=inc&ff1\=url&fo1\=contain&fv1\=spree
|  | Sosse Capture Page Screenshot | guide_ai_api_doc_results.png

|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  | Click Link | https://demo.spreecommerce.org/products/horned-glasses
|  | Click Link | 📡 Webhooks
|  | Sosse Capture Page Screenshot | guide_ai_api_doc_webhook.png
|  | Click Link | 📊 Metadata
|  | Sosse Capture Page Screenshot | guide_ai_api_doc_metadata.png
