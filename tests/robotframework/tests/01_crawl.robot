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
|  | Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_url
|  | Input Text | id=id_url | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | SOSSE Wait Until Page Contains | Create a new policy
|  | SOSSE Capture Page Screenshot | crawl_new_url.png
|  | Click Element | xpath=//input[@value='Confirm']
|  | SOSSE Wait Until Page Contains | Crawl status
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_status/
|  | Page Should Not Contain | No crawlers running.
|  | Page Should Not Contain | exited
|  | SOSSE Wait Until Page Contains | 4 recurring documents | 5min
|  | SOSSE Wait Until Page Contains | 0 pending documents | 2min
|  | SOSSE Wait Until Page Contains | idle
|  | Reload Page
|  | SOSSE Wait Until Page Contains | Crawl status
|  | Scroll To Bottom
|  | SOSSE Capture Page Screenshot | crawl_status.png

| Crawl a binary URL
|  | Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_url
|  | Input Text | id=id_url | http://127.0.0.1/static/Cat%20photos.zip
|  | Click Element | xpath=//input[@value='Check and queue']
|  | SOSSE Wait Until Page Contains | Create a new policy
|  | Click Element | xpath=//input[@value='Confirm']
|  | SOSSE Wait Until Page Contains | Crawl status
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_status/
|  | Page Should Not Contain | No crawlers running.
|  | Page Should Not Contain | exited
|  | SOSSE Wait Until Page Contains | 0 pending documents | 2min
|  | SOSSE Wait Until Page Contains | idle
|  | Reload Page
|  | SOSSE Wait Until Page Contains | Crawl status
|  | Scroll To Bottom

| Crawl policies
|  | Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | Wait Until Element Is Visible | id=result_list
|  | SOSSE Capture Page Screenshot | crawl_policy_list.png
|  | Click Element | xpath=//table[@id='result_list']//a[.='(default)']
|  | SOSSE Capture Page Screenshot | crawl_policy_decision_no_hilight.png
|  | Scroll To Elem | id=tabs
|  | SOSSE Capture Page Screenshot | crawl_policy_decision.png

|  | Reload Page
|  | Scroll To Elem | id=tabs
|  | Click Link | 🌍 Browser
|  | SOSSE Capture Page Screenshot | crawl_policy_browser.png

|  | Reload Page
|  | Scroll To Elem | id=tabs
|  | Click Link | 🔖 HTML snapshot
|  | SOSSE Capture Page Screenshot | crawl_policy_html_snapshot.png

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
|  | Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_url
|  | Input Text | id=id_url | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | SOSSE Capture Page Screenshot | crawl_on_depth_add.png

|  | Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Wait Until Element Is Visible | id=id_url_regex
|  | Input Text | id=id_url_regex | https://en.wikipedia.org/.*
|  | Input Text | id=id_recursion_depth | 2
|  | Capture Element Screenshot | //fieldset[1] | policy_all.png

| Documents
|  | Go To | http://127.0.0.1/admin/se/document/
|  | Wait Until Element Is Visible | id=result_list
|  | SOSSE Capture Page Screenshot | documents_list.png
|  | ${doc_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${doc_count} | 5

| Domain
|  | Go To | http://127.0.0.1/admin/se/domainsetting/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 1
|  | Click Link | 127.0.0.1
|  | SOSSE Capture Page Screenshot | domain_setting.png

| Cookies
|  | Run Keyword And Ignore Error | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../cookies.json | shell=True
|  | Go To | http://127.0.0.1/admin/se/cookie/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 3
|  | SOSSE Capture Page Screenshot | cookies_list.png
|  | Click Link | Import cookies
|  | SOSSE Capture Page Screenshot | cookies_import.png

| Excluded URLs
|  | Go To | http://127.0.0.1/admin/se/excludedurl/add/
|  | Wait Until Element Is Visible | id=footer
|  | SOSSE Capture Page Screenshot | excluded_url.png

| Search Engine
|  | Go To | http://127.0.0.1/admin/se/searchengine/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Not Be Equal As Numbers | ${dom_count} | 0
|  | Wait Until Element Is Visible | id=footer
|  | SOSSE Capture Page Screenshot | search_engines_list.png
|  | Click Link | Brave
|  | SOSSE Wait Until Page Contains | Long name
|  | SOSSE Capture Page Screenshot | search_engine.png

| Authentication
|  | Go To | http://127.0.0.1/admin/auth/user/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 1
|  | Click Link | admin
|  | SOSSE Wait Until Page Contains | Important dates
|  | SOSSE Capture Page Screenshot | user_management.png
