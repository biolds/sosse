| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot

| *Test Cases* |
| Data extraction
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import Link ; Link.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.document import Document ; Document.objects.wo_content().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.html_asset import HTMLAsset ; HTMLAsset.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.crawl_policy import CrawlPolicy ; CrawlPolicy.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/data_extraction_data/dump.json | shell=True

|  | Sosse Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | Click Link | https://ted.europa.eu/en/notice/-/detail/[0-9]*-.*
|  | Click Link | 🌍 Browser
|  | Sosse Capture Page Screenshot | guide_data_extract_crawl_policy.png

|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  | Click Link | https://ted.europa.eu/en/notice/-/detail/124149-2025
|  | Click Link | 📊 Metadata
|  | Execute JavaScript | window.scrollTo(0, document.body.scrollHeight)
|  | Sosse Capture Page Screenshot | guide_data_extract_document_metadata.png

|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  | Click Element | xpath=//a[starts-with(., 'https://ted.europa.eu/en/search/result?FT=Germany')]
|  | Click Link | Archive
|  | Click Link | Links from here
|  | Click Element | id=atom_button
|  | Mouse Over | xpath=//a[text()='CSV export']
|  | Sosse Capture Page Screenshot | guide_data_extract_csv_export.png
