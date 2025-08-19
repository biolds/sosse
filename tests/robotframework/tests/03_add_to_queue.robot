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
| Show on homepage
|  | Crawl Test Website
|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  | Click Link | http://127.0.0.1/screenshots/website/index.html
|  | Element Should Be Visible | xpath=//input[@id='id_show_on_homepage' and @checked]
|  | Sosse Go To | http://127.0.0.1/
|  | Page Should Contain | http://127.0.0.1/screenshots/website/index.html

| Show on homepage disabled
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Click Element | id=id_show_on_homepage
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Add to Crawl Queue']
|  | Sosse Wait Until Page Contains | URL was queued
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Wait For Queue | 1
|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  | Click Link | http://127.0.0.1/screenshots/website/index.html
|  | Element Should Not Be Visible | xpath=//input[@id='id_show_on_homepage' and @checked]
|  | Sosse Go To | http://127.0.0.1/
|  | Page Should Not Contain | http://127.0.0.1/screenshots/website/index.html

| Invalid URL
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http
|  | Select From List By Label | id=id_collection | Default
|  | Click Element | xpath=//input[@value='Add to Crawl Queue']
|  | Page Should Contain | url has no scheme

| Form prefill
|  | [Tags] | returnurl
|  | ${collection_id}= | Get Default Collection Id
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/?urls\=http://127.0.0.1/test&collection\=${collection_id}&show_on_homepage\=false
|  | Element Should Contain | id=id_urls | http://127.0.0.1/test
|  | ${selected_collection}= | Get Selected List Value | id=id_collection
|  | Should Be Equal | ${selected_collection} | ${collection_id}
|  | Element Should Not Be Visible | xpath=//input[@id='id_show_on_homepage' and @checked]
# Check links
|  | ${create_collection}= | Get Element Attribute | id=create-collection-link | href
|  | Should Be Equal | ${create_collection} | http://127.0.0.1/admin/se/collection/add/?return_url\=%2Fadmin%2Fse%2Fdocument%2Fqueue%2F%3Furls%3Dhttp%253A%252F%252F127.0.0.1%252Ftest%26collection%3D${collection_id}%26show_on_homepage%3Dfalse&unlimited_regex\=%5Ehttp%3A%2F%2F127%5C.0%5C.0%5C.1%2Ftest
|  | ${edit_collection}= | Get Element Attribute | xpath=//div[starts-with(@id, 'collection-desc-') and @style='display: block;']//a | href
|  | Should Be Equal | ${edit_collection} | http://127.0.0.1/admin/se/collection/${collection_id}/change/?return_url\=%2Fadmin%2Fse%2Fdocument%2Fqueue%2F%3Furls%3Dhttp%253A%252F%252F127.0.0.1%252Ftest%26collection%3D${collection_id}%26show_on_homepage%3Dfalse

# Update Form
|  | Input Text | id=id_urls | http://127.0.0.2/
|  | Click Element | id=id_show_on_homepage

# Check links
|  | ${create_collection}= | Get Element Attribute | id=create-collection-link | href
|  | Should Be Equal | ${create_collection} | http://127.0.0.1/admin/se/collection/add/?return_url\=%2Fadmin%2Fse%2Fdocument%2Fqueue%2F%3Furls%3Dhttp%253A%252F%252F127.0.0.2%252F%26collection%3D${collection_id}%26show_on_homepage%3Dtrue&unlimited_regex\=%5Ehttp%3A%2F%2F127%5C.0%5C.0%5C.2%2F
|  | ${edit_collection}= | Get Element Attribute | xpath=//div[starts-with(@id, 'collection-desc-') and @style='display: block;']//a | href
|  | Should Be Equal | ${edit_collection} | http://127.0.0.1/admin/se/collection/${collection_id}/change/?return_url\=%2Fadmin%2Fse%2Fdocument%2Fqueue%2F%3Furls%3Dhttp%253A%252F%252F127.0.0.2%252F%26collection%3D${collection_id}%26show_on_homepage%3Dtrue

# Check return URL works
|  | Click Link | Create new Collection
|  | Element Should Contain | id=id_unlimited_regex | ^http://127\\.0\\.0\\.2/
|  | Input Text | id=id_name | Collection test
|  | Click Element | xpath=//input[@value='Save']
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/queue/?urls\=http%3A%2F%2F127.0.0.2%2F&collection\=${collection_id}&show_on_homepage\=true
|  | Element Should Contain | id=id_urls | http://127.0.0.2/
|  | Element Should Be Visible | xpath=//input[@id='id_show_on_homepage' and @checked]
