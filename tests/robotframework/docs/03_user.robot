| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Resource | ../tests/collection.robot
| Resource | ../tests/documents.robot
| Resource | ../tests/webhooks.robot
| Suite Setup | Suite Setup Steps

| *Keywords* |
| Suite Setup Steps
|  | Clear Documents
|  | Clear Collections
|  | Clear Webhooks
|  | Crawl Test Website

| *Test Cases* |
| Search
|  | Sosse Go To | http://127.0.0.1/
|  | Wait Until Element Is Visible | id=id_q
|  | Input Text | id_q | website
|  | Click Button | search_button
|  | Sosse Wait Until Page Contains | 4 sites found
|  | ${res_count}= | Get Element Count | xpath=//div[@class='res']
|  | Should Be Equal As Numbers | ${res_count} | 4
|  | Sosse Capture Page Screenshot | search.png
|  | Click Element | id=more
|  | Select From List By Value | id=doc_lang | en
|  | Input Text | xpath=//input[@name='fv1'] | cats
|  | Click Element | xpath=//div[@id='adv_search1']/input[@value='+']
|  | Select From List By Label | xpath=//select[@name='ft2'] | Exclude
|  | Select From List By Label | xpath=//select[@name='ff2'] | Mimetype
|  | Select From List By Label | xpath=//select[@name='fo2'] | Matching Regex
|  | Input Text | xpath=//input[@name='fv2'] | text/markdown
|  | Capture Element Screenshot | id=adv_search | extended_search.png
|  | Capture Element Screenshot | xpath=//div[@id='adv_search2']/input[@value='+'] | extended_search_plus_button.png
|  | Capture Element Screenshot | xpath=//div[@class='res'][2] | search_result.png
|  | Capture Element Screenshot | id=atom_button | atom_button.png

| Shortcuts
|  | Reload page
|  | Input Text | id_q | !b cats
|  | Capture Element Screenshot | id=search_form | shortcut.png

| Profile
|  | Click Button | id=user_menu_button
|  | Click Link | Profile
|  | Sosse Wait Until Page Contains | Search terms parsing language
|  | Sosse Capture Page Screenshot | profile.png

| History
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import SearchHistory ; SearchHistory.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../../searchhistory.json | shell=True
|  | Sosse Go To | http://127.0.0.1/history/
|  | Sosse Wait Until Page Contains | 3 elements in the history
|  | Sosse Capture Page Screenshot | history.png
|  | Capture Element Screenshot | xpath=//input[@class='del_button img_button' and @value=''] | history_delete.png
|  | Capture Element Screenshot | id=del_all | history_delete_all.png

| Archive
|  | Sosse Go To | http://127.0.0.1/screenshot/http://127.0.0.1/screenshots/website/cats.html
|  | Click Element | id=fold_button
|  | Sosse Capture Page Screenshot | archive_header.png
|  | Reload Page
|  | Select Frame | xpath=//iframe[1]
|  | Wait Until Element Is Visible | xpath=//a[@class='img_link'][2]
|  | Scroll To Bottom
|  | Mouse Over | xpath=//a[@class='img_link'][2]
|  | Sosse Capture Page Screenshot | archive_screenshot.png
|  | Unselect Frame

| Binary archive
|  | Sosse Go To | http://127.0.0.1/download/http://127.0.0.1/static/Cat%20photos.zip
|  | Sosse Wait Until Page Contains | Download | 5min
|  | Sosse Capture Page Screenshot | archive_download.png

| Syndication feed
|  | [Tags] | syndication_feed
|  | Sosse Go To | http://127.0.0.1/
|  | Click Element | id=more
|  | Select From List By Label | id=id_s | First crawled descending
|  | Select From List By Label | xpath=//select[@name='ff1'] | Linked by url
|  | Select From List By Label | xpath=//select[@name='fo1'] | Equal to
|  | Input Text | xpath=//input[@name='fv1'] | https://exemple.com/atom.xml
|  | Sosse Capture Page Screenshot |
|  | Capture Element Screenshot | id=search_form | syndication_feed.png

| Swagger
|  | [Tags] | swagger
|  | Sosse Go To | http://127.0.0.1/admin/
|  | Click Link | Rest API
|  | Wait Until Element Is Visible | id=swagger-ui
|  | Wait Until Element Is Visible | id=operations-api-api_document_list
|  | Sosse Capture Page Screenshot | swagger.png
|  | Click Element | id=operations-api-api_document_list
|  | Click Button | class=try-out__btn
|  | Click Button | class=execute
|  | Wait Until Element Is Visible | class=live-responses-table
|  | Element Should Contain | class=live-responses-table | Dummy static website

| Browsable home
|  | [Tags] | browsable_home
|  | Clear Documents
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../home_favicon.json | shell=True
|  | Load Data With Collection | ${CURDIR}/../home_docs.json
|  | Run Command | sed | -e | s/^#browsable_home.*/browsable_home\=true/ | -i | /etc/sosse/sosse.conf
|  | Run Command | killall | -s | HUP | uwsgi
|  | Sosse Go To | http://127.0.0.1/
|  | Sosse Capture Page Screenshot | browsable_home.png

| Online mode
|  | [Tags] | online_mode
|  | Run Command | sed | -e | s/^#online_search_redirect.*/online_search_redirect\=DuckDuckGo/ | -i | /etc/sosse/sosse.conf
|  | Run Command | killall | -s | HUP | uwsgi
|  | Sosse Go To | http://127.0.0.1/profile/
|  | Hilight | id=online_mode
|  | Sosse Capture Page Screenshot | online_mode.png
|  | Capture Element Screenshot | id=user_menu | online_mode_status.png
|  | Run Command | sed | -e | s/^online_search_redirect.*/#online_search_redirect\=DuckDuckGo/ | -i | /etc/sosse/sosse.conf
|  | Run Command | killall | -s | HUP | uwsgi

| Document Webhook
|  | Sosse Go To | http://127.0.0.1/admin/se/document/327/change/
|  | Scroll To Elem | id=tabs
|  | Click Link | 📡 Webhooks
|  | Sosse Capture Page Screenshot | webhooks_result.png
