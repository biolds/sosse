| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot

| *Test Cases* |
| Create Crawl Policy
|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Input Text | id=id_url_regex | http://127.0.0.1/screenshots/website/.*
|  | Click Element | xpath=//input[@value="Save"]
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/crawlpolicy/

| Crawl a new URL
|  | SOSSE Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | SOSSE Wait Until Page Contains | Create a new policy
|  | Click Element | xpath=//input[@value='Confirm']
|  | SOSSE Wait Until Page Contains | Crawl queue
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Page Should Not Contain | No crawlers running.
|  | Page Should Not Contain | exited
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_recurring_count" and contains(., '4')] | 5min
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_pending_count" and contains(., '0')] | 2min
|  | SOSSE Capture Page Screenshot | test_crawl_queue.png
