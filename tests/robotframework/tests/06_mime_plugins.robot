| *Settings* |
| Library | SeleniumLibrary
| Library | String
| Resource | common.robot
| Resource | collection.robot
| Resource | documents.robot
| Resource | crawl_queue.robot
| Test Setup | Setup

| *Keywords* |
| Setup
|  | Clear Collections
|  | Clear Documents


| *Test Cases* |
| MIME Plugin - Crawl PNG with metadata
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/img-meta.png
|  | Select From List By Label | id=id_collection | Default
|  | Click Element | xpath=//input[@value='Add to Crawl Queue']
|  | Sosse Wait Until Page Contains | Crawl queue
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Wait For Queue | 1
|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  | Click Link | http://127.0.0.1/screenshots/img-meta.png
|  | Element Should Contain | xpath=//fieldset//div[contains(@class, 'field-_title')]//span | Title test
