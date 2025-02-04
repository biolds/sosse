| *Settings* |
| Library | SeleniumLibrary
| Library | String
| Resource | common.robot
| Resource | crawl_policy.robot
| Resource | documents.robot
| Resource | tags.robot

| *Test Cases* |
| Create tags
|  | Create sample tags

| Create Crawl Policy
|  | Clear Crawl Policies
|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Input Text | id=id_url_regex | http://127.0.0.1/screenshots/website/.*
|  | Click Element | xpath=//input[@value="Save"]
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/crawlpolicy/

| Crawl a new URL
|  | Clear Documents
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

| Modal test
|  | SOSSE Go To | http://127.0.0.1/
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=tags
|  | Click Element | xpath=//button[contains(., 'Cancel')]
|  | Element Should Not Be Visible | id=tags

| Set document tags
|  | SOSSE Go To | http://127.0.0.1/
|  | Click Element | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | Click Element | id=fold_button
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags
|  | Click Element | xpath=//div[@id='tags_list']/div/div[1]/div
|  | Click Element | xpath=//div[@id='tags_list']/div/div[2]/div
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@id='document_tags']//div[@class='tag tag-select'][1]
|  | Element Should Contain | xpath=//div[@id='document_tags']//div[@class='tag tag-select'][1] | AI
|  | Element Should Be Visible | xpath=//div[@id='document_tags']//div[@class='tag tag-select'][2]
|  | Element Should Contain | xpath=//div[@id='document_tags']//div[@class='tag tag-select'][2] | General Usage
|  | Reload Page
|  | Click Element | id=fold_button
|  | Element Should Be Visible | xpath=//div[@id='document_tags']//div[@class='tag tag-select'][1]
|  | Element Should Contain | xpath=//div[@id='document_tags']//div[@class='tag tag-select'][1] | AI
|  | Element Should Be Visible | xpath=//div[@id='document_tags']//div[@class='tag tag-select'][2]
|  | Element Should Contain | xpath=//div[@id='document_tags']//div[@class='tag tag-select'][2] | General Usage

| Tag search modal
|  | SOSSE Go To | http://127.0.0.1/
|  | Element Should Be Visible | id=search_tags
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=tags
# Check counters
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[1] | General Usage
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[1]//span[@class='tag-counter'] | 1
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2] | AI
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2]//span[@class='tag-counter'] | 1
# Activate tags check
|  | ${tag_id}= | Get Element Attribute | xpath=//div[@id='tags_list']//div[@class='tag' and contains(., 'General Usage')] | id
|  | Click Element | xpath=//div[@id='tags_list']//div[@class='tag' and contains(., 'General Usage')]
|  | ${tag_pk}= | Replace String | ${tag_id} | tag- | ${EMPTY}
|  | Element Should Be Visible | xpath=//div[@id='tag-edit-${tag_pk}' and contains(., 'General Usage')]
|  | Click Element | id=tags_submit
# Search results
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/?tag=${tag_pk}&l=en&ps=20
|  | Element Should Be Visible | xpath=//div[@id='search_tags']//div[@id='tag-search-${tag_pk}' and contains(., 'General Usage')]
|  | Element Should Be Visible | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | ${results_count}= | Get Element Count | xpath=//div[@id='home-grid']/a
|  | Should Be Equal As Integers | ${results_count} | 1
# Reopen modal - Delete filter
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@id='tag-edit-${tag_pk}' and contains(., 'General Usage')]
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[1] | General Usage
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[1]//span[@class='tag-counter'] | 1
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2] | AI
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2]//span[@class='tag-counter'] | 1
|  | Element Should Be Visible | id=tag-edit-${tag_pk}
|  | Click Element | xpath=//div[@id='tag-edit-${tag_pk}']//a[@class='tag_delete']
|  | Element Should Not Be Visible | id=tag-edit-${tag_pk}
|  | Click Element | id=tags_submit
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/?l=en&ps=20

# Reopen modal - Clear all
|  | Go To | http://127.0.0.1/?tag\=${tag_pk}&l\=en&ps=\20
|  | Wait Until Element Is Visible | id=search_tags
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=editing_tags
|  | Element Should Be Visible | id=tag-edit-${tag_pk}
|  | Click Element | id=clear_selected_tags
|  | Element Should Not Be Visible | id=tag-edit-${tag_pk}
|  | Click Element | id=tags_submit
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/?l=en&ps=20

# Reopen modal - Clear all
|  | Go To | http://127.0.0.1/?tag\=${tag_pk}&l\=en&ps=\20
|  | Wait Until Element Is Visible | id=search_tags
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=editing_tags
|  | Element Should Be Visible | id=tag-edit-${tag_pk}
|  | Click Element | id=clear_selected_tags
|  | Element Should Not Be Visible | id=tag-edit-${tag_pk}
|  | Click Element | id=tags_submit
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/?l=en&ps=20

# Repopen modal - Unselect tag
|  | Go To | http://127.0.0.1/?tag\=${tag_pk}&l\=en&ps=\20
|  | Wait Until Element Is Visible | id=search_tags
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=editing_tags
|  | Element Should Be Visible | id=tag-edit-${tag_pk}
|  | Click Element | id=tag-${tag_pk}
|  | Element Should Not Be Visible | id=tag-edit-${tag_pk}
|  | Click Element | id=tags_submit
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/?l=en&ps=20

| Admin - Tag link
|  | SOSSE Go To | http://127.0.0.1/
|  | Click Element | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | Click Element | id=fold_button
|  | Click Element | xpath=//div[@id='top_bar_links']//a[contains(.,'Administration')]
|  | ${loc}= | Get Location
|  | Should Match Regexp | ${loc} | http://127.0.0.1/admin/se/document/[0-9]+/change/
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select'][1]
|  | ${loc}= | Get Location
|  | Should Match Regexp | ${loc} | http://127.0.0.1/admin/se/document/\\?tags\=[0-9]+
|  | Page Should Contain | 1 result

| Admin - Add tag to document
|  | SOSSE Go To | http://127.0.0.1/
|  | Click Element | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | Click Element | id=fold_button
|  | Click Element | xpath=//div[@id='top_bar_links']//a[contains(.,'Administration')]
|  | ${loc}= | Get Location
|  | Should Match Regexp | ${loc} | http://127.0.0.1/admin/se/document/[0-9]+/change/
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//div[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | xpath=//div[@class='tag' and contains(., 'CPU')]
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//div[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 3
|  | Click Element | xpath=//button[contains(., 'Ok')]
|  | Wait Until Element Is Not Visible | id=tags
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 3
|  | Click Element | xpath=//input[@value='Save and continue editing']
|  | Wait Until Page Contains | You may edit it again below
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 3

| Admin - Remove tag from document
|  | SOSSE Go To | http://127.0.0.1/
|  | Click Element | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | Click Element | id=fold_button
|  | Click Element | xpath=//div[@id='top_bar_links']//a[contains(.,'Administration')]
|  | ${loc}= | Get Location
|  | Should Match Regexp | ${loc} | http://127.0.0.1/admin/se/document/[0-9]+/change/
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 3
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//div[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 3
|  | Click Element | xpath=//div[@class='tag' and contains(., 'CPU')]
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//div[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | xpath=//button[contains(., 'Ok')]
|  | Wait Until Element Is Not Visible | id=tags
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | xpath=//input[@value='Save and continue editing']
|  | Wait Until Page Contains | You may edit it again below
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 2

| Admin - Clear tags
|  | SOSSE Go To | http://127.0.0.1/
|  | Click Element | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | Click Element | id=fold_button
|  | Click Element | xpath=//div[@id='top_bar_links']//a[contains(.,'Administration')]
|  | ${loc}= | Get Location
|  | Should Match Regexp | ${loc} | http://127.0.0.1/admin/se/document/[0-9]+/change/
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//div[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | id=clear_selected_tags
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//div[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 0
|  | Click Element | xpath=//button[contains(., 'Ok')]
|  | Wait Until Element Is Not Visible | id=tags
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 0
|  | Click Element | xpath=//input[@value='Save and continue editing']
|  | Wait Until Page Contains | You may edit it again below
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 0

| Admin - Create crawl policy with tag
|  | Clear Crawl Policies
|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Input Text | id=id_url_regex | http://example.com/.*
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags
|  | Click Element | xpath=//div[@id='tags_list']//div[@class='tag' and contains(., 'AI')]
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select']
|  | Element Should Contain | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select'] | AI
|  | Click Element | xpath=//input[@value="Save"]
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/crawlpolicy/
|  | ${active_tags}= | Get WebElement | xpath=//th[@class='field-url_regex' and contains(., 'http://example.com/.*')]/../td[@class='field-active_tags']
|  | Element Should Contain | ${active_tags} | AI

| Admin - Edit crawl policy with tag
|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | Click Link | http://example.com/.*
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags
|  | Click Element | xpath=//div[@id='tags_list']//div[@class='tag' and contains(., 'General Usage')]
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select'][1]
|  | Element Should Contain | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select'][1] | AI
|  | Element Should Be Visible | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select'][2]
|  | Element Should Contain | xpath=//div[@class='form-row field-_tags']//div[@class='tag tag-select'][2] | General Usage
|  | Click Element | xpath=//input[@value="Save"]
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/crawlpolicy/
|  | ${tags_cell}= | Set Variable | //th[@class='field-url_regex' and contains(., 'http://example.com/.*')]/../td[@class='field-active_tags']
|  | Element Should Contain | xpath=${tags_cell}//div[@class='tag'][1] | AI
|  | Element Should Contain | xpath=${tags_cell}//div[@class='tag'][2] | General Usage
