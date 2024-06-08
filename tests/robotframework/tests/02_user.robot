| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot

| *Test Cases* |
| Search
|  | Go To | http://127.0.0.1/
|  | Wait Until Element Is Visible | id=id_q
|  | Input Text | id_q | website
|  | Click Button | search_button
|  | Wait Until Page Contains | 4 sites found
|  | ${res_count}= | Get Element Count | xpath=//div[@class='res']
|  | Should Be Equal As Numbers | ${res_count} | 4
|  | Capture Page Screenshot | search.png
|  | Click Element | id=more
|  | Select From List By Value | id=doc_lang | en
|  | Input Text | xpath=//input[@name='fv1'] | cats
|  | Click Element | xpath=//div[@id='adv_search1']/input[@value='+']
|  | Select From List By Label | xpath=//select[@name='ft2'] | Exclude
|  | Select From List By Label | xpath=//select[@name='ff2'] | Mimetype
|  | Select From List By Label | xpath=//select[@name='fo2'] | Matching Regexp
|  | Input Text | xpath=//input[@name='fv2'] | text/markdown
|  | Capture Element Screenshot | id=adv_search | extended_search.png
|  | Capture Element Screenshot | xpath=//div[@id='adv_search2']/input[@value='+'] | extended_search_plus_button.png
|  | Capture Element Screenshot | xpath=//div[@class='res'][2] | search_result.png
|  | Capture Element Screenshot | id=stats_button | stats_button.png
|  | Capture Element Screenshot | id=atom_button | atom_button.png
|  | Click Element | id=stats_button
|  | Wait Until Page Does Not Contain | Please wait
|  | Capture Element Screenshot | id=word_stats | word_stats.png

| Shortcuts
|  | Reload page
|  | Input Text | id_q | !b cats
|  | Capture Element Screenshot | id=search_form | shortcut.png

| Preferences
|  | Click Button | id=user_menu_button
|  | Click Link | Preferences
|  | Wait Until Page Contains | Search terms parsing language
|  | Capture Page Screenshot | preferences.png

| Statistics
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../../document-ja.json | shell=True
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import CrawlerStats ; from django.utils.timezone import now ; CrawlerStats.create(now()) | shell=True
|  | Go To | http://127.0.0.1/stats/
|  | Wait Until Page Does Not Contain | xpath=//*[@class='loader'] | timeout=5 min
|  | Sleep | 5s
|  | Capture Page Screenshot | statistics.png

| History
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../../searchhistory.json | shell=True
|  | Go To | http://127.0.0.1/history/
|  | Wait Until Page Contains | 4 elements in the history
|  | Capture Page Screenshot | history.png
|  | Capture Element Screenshot | xpath=//input[@class='del_button img_button' and @value=''] | history_delete.png
|  | Capture Element Screenshot | id=del_all | history_delete_all.png

| Cache
|  | Go To | http://127.0.0.1/screenshot/http://127.0.0.1/screenshots/website/cats.html
|  | Click Element | id=fold_button
|  | Capture Page Screenshot | cache_header.png
|  | Reload Page
|  | Select Frame | xpath=//iframe[1]
|  | Scroll To Bottom
|  | Mouse Over | xpath=//a[@class='img_link'][2]
|  | Capture Page Screenshot | cache_screenshot.png
|  | Unselect Frame

| Syndication feed
|  | [Tags] | syndication_feed
|  | Go To | http://127.0.0.1/
|  | Click Element | id=more
|  | Select From List By Label | id=id_s | First crawled descending
|  | Select From List By Label | xpath=//select[@name='ff1'] | Linked by url
|  | Select From List By Label | xpath=//select[@name='fo1'] | Equal to
|  | Input Text | xpath=//input[@name='fv1'] | https://exemple.com/atom.xml
|  | Capture Page Screenshot |
|  | Capture Element Screenshot | id=search_form | syndication_feed.png

| Browsable home
|  | [Tags] | browsable_home
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../home_favicon.json | shell=True
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../home_docs.json | shell=True
|  | Run Command | sed | -e | s/^#browsable_home.*/browsable_home\=true/ | -i | /etc/sosse/sosse.conf
|  | Run Command | killall | -s | HUP | uwsgi
|  | Go To | http://127.0.0.1/
|  | Capture Page Screenshot | browsable_home.png

| Online mode
|  | [Tags] | online_mode
|  | Run Command | sed | -e | s/^#online_search_redirect.*/online_search_redirect\=DuckDuckGo/ | -i | /etc/sosse/sosse.conf
|  | Run Command | killall | -s | HUP | uwsgi
|  | Go To | http://127.0.0.1/prefs/
|  | Hilight | id=online_mode
|  | Capture Page Screenshot | online_mode.png
|  | Capture Element Screenshot | id=user_menu | online_mode_status.png

| Swagger
|  | [Tags] | swagger
|  | Go To | http://127.0.0.1/
|  | Click Button | id=user_menu_button
|  | Click Link | Rest API
|  | Wait Until Element Is Visible | id=swagger-ui
|  | Wait Until Element Is Visible | id=operations-api-api_document_list
|  | Capture Page Screenshot | swagger.png
|  | Click Element | id=operations-api-api_document_list
|  | Click Button | class=try-out__btn
|  | Click Button | class=execute
|  | Wait Until Element Is Visible | class=live-responses-table
|  | Element Should Contain | class=live-responses-table | Dummy static website
