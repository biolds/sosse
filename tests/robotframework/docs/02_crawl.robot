| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Resource | ../tests/tags.robot

| *Test Cases* |
| Admin UI access
|  | Capture Element Screenshot | id=user_menu_button | user_menu_button.png
|  | Capture Element Screenshot | id=conf_menu_button | conf_menu_button.png
|  | Click Element | id=conf_menu_button
|  | Click Link | Administration
|  | Sosse Capture Page Screenshot | admin_ui.png

| Crawl a new URL
|  | Sosse Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Input Text | id=id_url_regex | http://127.0.0.1/screenshots/website/.*
|  | Click Link | 🌍 Browser
|  | Select From List By Label | id=id_default_browse_mode | Chromium
|  | Select Checkbox | id=id_take_screenshots
|  | Input Text | id=id_script | return {metadata: {"product_name": "Cat toy", "sku": "CATTOY-001", "price": 4.99, "currency": "EUR", "category": "Animals"}}
|  | Click Element | xpath=//input[@value="Save"]
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Sosse Wait Until Page Contains | Create a new policy
|  | Sosse Capture Page Screenshot | crawl_new_url.png
|  | Click Element | xpath=//input[@value='Confirm']
|  | Wait Until Element Is Visible | xpath=//h3[text()='Crawl queue']
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Page Should Not Contain | No crawlers running.
|  | Page Should Not Contain | exited
|  | Sosse Go To | http://127.0.0.1/admin/se/document/crawlers/
|  | Sosse Capture Page Screenshot | crawlers.png
|  | Sosse Go To | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_recurring_count" and contains(., '4')] | 5min
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_pending_count" and contains(., '0')] | 2min
|  | Sosse Capture Page Screenshot | crawl_queue.png

| Crawl a binary URL
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/static/Cat%20photos.zip
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Sosse Wait Until Page Contains | Create a new policy
|  | Click Element | xpath=//input[@value='Confirm']
|  | Wait Until Element Is Visible | xpath=//h3[text()='Crawl queue']
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_pending_count" and contains(., '0')] | 2min
|  | Scroll To Bottom

| Analytics
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../../document-ja.json | shell=True
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.models import CrawlerStats ; from django.utils.timezone import now ; CrawlerStats.create(now()) | shell=True
|  | Sosse Go To | http://127.0.0.1/admin/se/document/analytics/
|  | Wait Until Page Does Not Contain | xpath=//*[@class='loader'] | timeout=5 min
|  | Sleep | 5s
|  | Sosse Capture Page Screenshot | analytics.png
|  | Run Command | ${SOSSE_ADMIN} | delete_documents | http://127.0.0.1/screenshots/website/jp.html

| Crawl policies
|  | Sosse Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | Wait Until Element Is Visible | id=result_list
|  | Sosse Capture Page Screenshot | crawl_policy_list.png
|  | Hilight | class=actions
|  | Sosse Capture Page Screenshot | crawl_policy_actions.png
|  | Click Element | xpath=//table[@id='result_list']//a[.='(default)']
# The default policy is read-only so the help text is hidden
|  | Page should not contain | URL regular expressions for this policy
|  | ${recursion} | Get Selected List Label | id=id_recursion
|  | Should Be Equal As Strings | ${recursion} | Depending on depth
|  | Sosse Capture Page Screenshot | crawl_policy_decision_no_hilight.png
|  | Scroll To Elem | id=tabs
|  | Sosse Capture Page Screenshot | crawl_policy_decision.png

# Non default policy should show the help
|  | Sosse Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Page should contain | URL regular expressions for this policy
|  | ${recursion} | Get Selected List Label | id=id_recursion
|  | Should Be Equal As Strings | ${recursion} | Crawl all pages

|  | Reload Page
|  | Scroll To Elem | id=tabs
|  | Click Link | 🌍 Browser
|  | Sosse Capture Page Screenshot | crawl_policy_browser.png

|  | Reload Page
|  | Scroll To Elem | id=tabs
|  | Click Link | 🔖 Archive
|  | Sosse Capture Page Screenshot | crawl_policy_archive.png

|  | Reload Page
|  | Scroll To Elem | id=tabs
|  | Click Link | 🕑 Recurrence
|  | Sosse Capture Page Screenshot | crawl_policy_updates.png

|  | Reload Page
|  | Scroll To Elem | id=tabs
|  | Click Link | 🔒 Authentication
|  | Sosse Capture Page Screenshot | crawl_policy_auth.png

| Crawl on depth
|  | Reload Page
|  | Select From List By Label | id=id_recursion | Depending on depth
|  | Capture Element Screenshot | //fieldset[1] | policy_on_depth.png
|  | Click Element | xpath=//input[@value="Save"]
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Sosse Capture Page Screenshot | crawl_on_depth_add.png

|  | Sosse Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Wait Until Element Is Visible | id=id_url_regex
|  | Input Text | id=id_url_regex | https://en.wikipedia.org/.*
|  | Input Text | id=id_recursion_depth | 2
|  | Capture Element Screenshot | //fieldset[1] | policy_all.png

| Documents
|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  | Wait Until Element Is Visible | id=result_list
|  | Sosse Capture Page Screenshot | documents_list.png
|  | Hilight | class=actions
|  | Sosse Capture Page Screenshot | documents_actions.png
|  | ${doc_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${doc_count} | 5
|  | Click Link | http://127.0.0.1/screenshots/website/cats.html
|  | Sosse Capture Page Screenshot | documents_details.png
|  | Page Should Contain | CATTOY-001
|  | Click Link | 📊 Metadata
|  | Sosse Capture Page Screenshot | metadata.png

| Domain
|  | Sosse Go To | http://127.0.0.1/admin/se/domainsetting/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 1
|  | Click Link | 127.0.0.1
|  | Sosse Capture Page Screenshot | domain_setting.png

| Cookies
|  | Run Keyword And Ignore Error | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../cookies.json | shell=True
|  | Sosse Go To | http://127.0.0.1/admin/se/cookie/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 3
|  | Sosse Capture Page Screenshot | cookies_list.png
|  | Click Link | Import cookies
|  | Sosse Capture Page Screenshot | cookies_import.png

| Excluded URLs
|  | Sosse Go To | http://127.0.0.1/admin/se/excludedurl/add/
|  | Wait Until Element Is Visible | id=footer
|  | Sosse Capture Page Screenshot | excluded_url.png

| Search Engine
|  | Sosse Go To | http://127.0.0.1/admin/se/searchengine/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Not Be Equal As Numbers | ${dom_count} | 0
|  | Wait Until Element Is Visible | id=footer
|  | Sosse Capture Page Screenshot | search_engines_list.png
|  | Click Link | Brave
|  | Sosse Wait Until Page Contains | Long name
|  | Sosse Capture Page Screenshot | search_engine.png

| Authentication
|  | Sosse Go To | http://127.0.0.1/admin/auth/user/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 1
|  | Click Link | admin
|  | Sosse Wait Until Page Contains | Important dates
|  | Scroll To Elem | xpath=//h2[contains(., 'Permissions')]
|  | Sosse Capture Page Screenshot | permissions.png

| Webhooks
|  | Sosse Go To | http://127.0.0.1/admin/se/webhook/add/
|  | Wait Until Element Is Visible | id=footer
|  | Input Text | id=id_name | Discord notification
|  | Input Text | id=id_url | https://discord.com/api/webhooks/1239873455671234522/V-gFSWDCS342jin98DWEsdrfs-23lmsWEalokj345kjn213oiu4
|  | Press Keys | id=id_url | HOME
|  | Select From List By Label | id=id_trigger_condition | On discovery
|  | Sosse Capture Page Screenshot | webhook_add.png
|  | Input Text | id=id_body_template | {"content":"New page discovered $title:\\n$url"}
|  | Click Element | xpath=//input[@value="Save"]
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 1
|  | Sosse Capture Page Screenshot | webhook_list.png


| Tags
|  | Create sample tags
|  | Sosse Go To | http://127.0.0.1/admin/se/tag/
|  | Wait Until Element Is Visible | id=result_list
|  | Sosse Capture Page Screenshot | tags_list.png
|  | Click Element | xpath=//th[@class='field-_name']//span[contains(., 'Motherboard')]
|  | Sosse Capture Page Screenshot | edit_tag.png
|  | Sosse Go To | http://127.0.0.1/
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=tags
|  | Wait Until Element Is Not Visible | class=loader
|  | Sosse Capture Page Screenshot | tags_filter.png
