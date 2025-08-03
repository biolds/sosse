| *Settings* |
| Library | SeleniumLibrary
| Library | String
| Resource | common.robot
| Resource | crawl_policy.robot
| Resource | documents.robot
| Resource | crawl_queue.robot
| Test Setup | Setup

| *Keywords* |
| Setup
|  | Clear Crawl Policies
|  | Clear Documents


| *Test Cases* |
| MIME Handler - Crawl PNG with metadata
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/img-meta.png
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Element Should Be Visible | xpath=//b[text()='Index only this URL']
|  | Click Element | xpath=//input[@value='Confirm']
|  | Sosse Wait Until Page Contains | Crawl queue
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Wait For Queue | 1
|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  | Click Link | http://127.0.0.1/screenshots/img-meta.png
|  | Element Should Contain | xpath=//fieldset//div[contains(@class, 'field-_title')]//span | Title test
