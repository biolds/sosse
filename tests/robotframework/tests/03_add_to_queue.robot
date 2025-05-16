| *Settings* |
| Library | SeleniumLibrary
| Library | String
| Resource | common.robot
| Resource | crawl_policy.robot
| Resource | documents.robot
| Test Setup | Setup

| *Keywords* |
| Setup
|  | Clear Crawl Policies
|  | Clear Documents

| Wait For Queue | [Arguments] | ${expected_count}
|  | Sosse Wait Until Page Contains | Crawl queue
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Page Should Not Contain | No crawlers running.
|  | Page Should Not Contain | exited
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_pending_count" and contains(., '0')] | 2min
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_new_count" and contains(., '0')] | 2min
|  | ${doc_count}= | Get Element Count | xpath=//table[@id="result_list"]//tr

| *Test Cases* |
| Default policy - Index only this URL
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Element Should Be Visible | xpath=//b[text()='Index only this URL']
|  | Element Should Be Visible | xpath=//b[text()='Index all pages of https://127.0.0.1/']
|  | Element Should Be Visible | id=id_recursion_depth
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[1]/span | General Usage
|  | Click Element | xpath=//div[@id='tags_list']/div/div[1]/span
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Element Should Contain | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'] | General Usage
# Check tags can be edited again
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 1
|  | Element Should Contain | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))] | General Usage
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Element Should Contain | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'] | General Usage
|  | Click Element | xpath=//input[@value='Confirm']
|  | Sosse Wait Until Page Contains | Crawl queue
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Wait For Queue | 1
|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  | Click Link | http://127.0.0.1/screenshots/website/index.html
|  | Element Should Be Visible | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Element Should Contain | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'] | General Usage

| Default policy - Index domain pages
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Element Should Be Visible | xpath=//b[text()='Index only this URL']
|  | Element Should Be Visible | xpath=//b[text()='Index all pages of https://127.0.0.1/']
|  | Element Should Be Visible | id=id_recursion_depth
|  | Click Element | xpath=//b[text()='Index all pages of https://127.0.0.1/']
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[1]/span | General Usage
|  | Click Element | xpath=//div[@id='tags_list']/div/div[1]/span
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Click Element | xpath=//input[@value='Confirm']
|  | Sosse Wait Until Page Contains | Crawl queue
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Wait For Queue | 4
# Check the policy
|  | Sosse Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | Element Should Be Visible | xpath=//p[@class='paginator' and contains(., '2 Crawl Policies')]
|  | Click Link | ^https?://127\\.0\\.0\\.1/
|  | ${recursion}= | Get Selected List Label | id=id_recursion
|  | Should Be Equal | ${recursion} | Crawl all pages
|  | Element Should Be Visible | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Element Should Contain | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'] | General Usage

# Existing policy
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/test
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Element Should Contain | id=matching_policy | This URL will be crawled with policy
|  | ${matching_policy}= | Get Text | xpath=//p[@id='matching_policy']/a
|  | Should Be Equal | ${matching_policy} | 「^https?://127\\.0\\.0\\.1/」

| Invalid URL
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Page Should Contain | url has no scheme
