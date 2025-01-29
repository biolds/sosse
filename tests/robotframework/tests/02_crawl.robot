| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot

| *Test Cases* |
| Admin UI access
|  | Capture Element Screenshot | id=user_menu_button | user_menu_button.png
|  | Capture Element Screenshot | id=conf_menu_button | conf_menu_button.png
|  | Click Element | id=conf_menu_button
|  | Click Link | Administration
|  | SOSSE Capture Page Screenshot | admin_ui.png

| Crawl a new URL
|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Input Text | id=id_url_regex | http://127.0.0.1/screenshots/website/.*
|  | Click Link | 🌍 Browser
|  | Select From List By Label | id=id_default_browse_mode | Chromium
|  | Select Checkbox | id=id_take_screenshots
|  | Click Element | xpath=//input[@value="Save"]
|  | SOSSE Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | SOSSE Wait Until Page Contains | Create a new policy
|  | SOSSE Capture Page Screenshot | crawl_new_url.png
|  | Click Element | xpath=//input[@value='Confirm']
|  | SOSSE Wait Until Page Contains | Crawl queue
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Page Should Not Contain | No crawlers running.
|  | Page Should Not Contain | exited
|  | SOSSE Go To | http://127.0.0.1/admin/se/document/crawlers/
|  | SOSSE Capture Page Screenshot | crawlers.png
|  | SOSSE Go To | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_recurring_count" and contains(., '4')] | 5min
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_pending_count" and contains(., '0')] | 2min
|  | SOSSE Capture Page Screenshot | crawl_queue.png

| Crawl a binary URL
|  | SOSSE Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/static/Cat%20photos.zip
|  | Click Element | xpath=//input[@value='Check and queue']
|  | SOSSE Wait Until Page Contains | Create a new policy
|  | Click Element | xpath=//input[@value='Confirm']
|  | SOSSE Wait Until Page Contains | Crawl queue
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_pending_count" and contains(., '0')] | 2min
|  | Scroll To Bottom

| Analytics
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../../document-ja.json | shell=True
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import CrawlerStats ; from django.utils.timezone import now ; CrawlerStats.create(now()) | shell=True
|  | SOSSE Go To | http://127.0.0.1/admin/se/document/analytics/
|  | Wait Until Page Does Not Contain | xpath=//*[@class='loader'] | timeout=5 min
|  | Sleep | 5s
|  | SOSSE Capture Page Screenshot | analytics.png
|  | Run Command | ${SOSSE_ADMIN} | delete_documents | http://127.0.0.1/screenshots/website/jp.html

| Crawl policies
|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | Wait Until Element Is Visible | id=result_list
|  | SOSSE Capture Page Screenshot | crawl_policy_list.png
|  | Click Element | xpath=//table[@id='result_list']//a[.='(default)']
# The default policy is read-only so the help text is hidden
|  | Page should not contain | URL regular expressions for this policy
|  | ${recursion} | Get Selected List Label | id=id_recursion
|  | Should Be Equal As Strings | ${recursion} | Never crawl
|  | SOSSE Capture Page Screenshot | crawl_policy_decision_no_hilight.png
|  | Scroll To Elem | id=tabs
|  | SOSSE Capture Page Screenshot | crawl_policy_decision.png

# Non default policy should show the help
|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Page should contain | URL regular expressions for this policy
|  | ${recursion} | Get Selected List Label | id=id_recursion
|  | Should Be Equal As Strings | ${recursion} | Crawl all pages

|  | Reload Page
|  | Scroll To Elem | id=tabs
|  | Click Link | 🌍 Browser
|  | SOSSE Capture Page Screenshot | crawl_policy_browser.png

|  | Reload Page
|  | Scroll To Elem | id=tabs
|  | Click Link | 🔖 Archive
|  | SOSSE Capture Page Screenshot | crawl_policy_archive.png

|  | Reload Page
|  | Scroll To Elem | id=tabs
|  | Click Link | 🕑 Recurrence
|  | SOSSE Capture Page Screenshot | crawl_policy_updates.png

|  | Reload Page
|  | Scroll To Elem | id=tabs
|  | Click Link | 🔒 Authentication
|  | SOSSE Capture Page Screenshot | crawl_policy_auth.png

| Crawl on depth
|  | Reload Page
|  | Select From List By Label | id=id_recursion | Depending on depth
|  | Capture Element Screenshot | //fieldset[1] | policy_on_depth.png
|  | Click Element | xpath=//input[@value="Save"]
|  | SOSSE Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | SOSSE Capture Page Screenshot | crawl_on_depth_add.png

|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Wait Until Element Is Visible | id=id_url_regex
|  | Input Text | id=id_url_regex | https://en.wikipedia.org/.*
|  | Input Text | id=id_recursion_depth | 2
|  | Capture Element Screenshot | //fieldset[1] | policy_all.png

| Documents
|  | SOSSE Go To | http://127.0.0.1/admin/se/document/
|  | Wait Until Element Is Visible | id=result_list
|  | SOSSE Capture Page Screenshot | documents_list.png
|  | ${doc_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${doc_count} | 5

| Domain
|  | SOSSE Go To | http://127.0.0.1/admin/se/domainsetting/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 1
|  | Click Link | 127.0.0.1
|  | SOSSE Capture Page Screenshot | domain_setting.png

| Cookies
|  | Run Keyword And Ignore Error | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../cookies.json | shell=True
|  | SOSSE Go To | http://127.0.0.1/admin/se/cookie/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 3
|  | SOSSE Capture Page Screenshot | cookies_list.png
|  | Click Link | Import cookies
|  | SOSSE Capture Page Screenshot | cookies_import.png

| Excluded URLs
|  | SOSSE Go To | http://127.0.0.1/admin/se/excludedurl/add/
|  | Wait Until Element Is Visible | id=footer
|  | SOSSE Capture Page Screenshot | excluded_url.png

| Search Engine
|  | SOSSE Go To | http://127.0.0.1/admin/se/searchengine/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Not Be Equal As Numbers | ${dom_count} | 0
|  | Wait Until Element Is Visible | id=footer
|  | SOSSE Capture Page Screenshot | search_engines_list.png
|  | Click Link | Brave
|  | SOSSE Wait Until Page Contains | Long name
|  | SOSSE Capture Page Screenshot | search_engine.png

| Authentication
|  | SOSSE Go To | http://127.0.0.1/admin/auth/user/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 1
|  | Click Link | admin
|  | SOSSE Wait Until Page Contains | Important dates
|  | Scroll To Elem | xpath=//h2[contains(., 'Permissions')]
|  | SOSSE Capture Page Screenshot | permissions.png
