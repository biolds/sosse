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
|  | Run Command | ../../sosse-admin | loaddata | tests/document-ja.json | shell=True
|  | Run Command | ../../sosse-admin | shell | -c | from se.models import CrawlerStats ; from django.utils.timezone import now ; CrawlerStats.create(now()) | shell=True
|  | Go To | http://127.0.0.1/stats/
|  | Capture Page Screenshot | statistics.png

| History
|  | Run Command | ../../sosse-admin | loaddata | tests/searchhistory.json | shell=True
|  | Go To | http://127.0.0.1/history/
|  | Wait Until Page Contains | 4 elements in the history
|  | Capture Page Screenshot | history.png
|  | Capture Element Screenshot | xpath=//input[@class='del_button img_button' and @value=''] | history_delete.png
|  | Capture Element Screenshot | id=del_all | history_delete_all.png

| Cache
|  | Go To | http://127.0.0.1/screenshot/http://127.0.0.1/screenshots/website/cats.html
|  | Hilight | id=cache_info
|  | Capture Page Screenshot | cache_info.png
|  | Reload Page
|  | Scroll To Bottom
|  | Mouse Over | xpath=//a[@class='img_link'][2]
|  | Capture Page Screenshot | cache_screenshot.png
