| *Settings* |
| Library | SeleniumLibrary
| Library | String
| Resource | common.robot
| Resource | collection.robot
| Resource | documents.robot
| Resource | tags.robot
| Resource | profile.robot

| *Test Cases* |
| Create tags
|  | Create sample tags

| Create Collection
|  | Clear Collections
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/add/
|  | Input Text | id=id_name | Test Collection
|  | Input Text | id=id_unlimited_regex | http://127.0.0.1/screenshots/website/.*
|  | Click Element | xpath=//input[@value="Save"]
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/collection/

| Crawl a new URL
|  | Clear Documents
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/website/index.html
|  | Select From List By Label | xpath=//select[@id='id_collection'] | Test Collection
|  | Click Element | xpath=//input[@value='Add to Crawl Queue']
|  | Sosse Wait Until Page Contains | Crawl queue
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Page Should Not Contain | No crawlers running.
|  | Page Should Not Contain | exited
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_recurring_count" and contains(., '4')] | 5min
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_pending_count" and contains(., '0')] | 2min

| Modal test
|  | Sosse Go To | http://127.0.0.1/
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | Click Element | xpath=//button[contains(., 'Cancel')]
|  | Element Should Not Be Visible | id=tags

| Set document tags
|  | Sosse Go To | http://127.0.0.1/
|  | Profile set search links to archive
|  | Click Element | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | Click Element | id=fold_button
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[1]/span | General Usage
|  | Wait Until Element Contains | xpath=//div[@id='tags_list']/div/div[1]/span//span[@class='tag-counter'] | 0
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2]/span | AI
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2]/span//span[@class='tag-counter'] | 0
|  | Click Element | xpath=//div[@id='tags_list']/div/div[1]/span
|  | Click Element | xpath=//div[@id='tags_list']/div/div[2]/span
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][1]
|  | Element Should Contain | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][1] | AI
|  | Element Should Be Visible | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][2]
|  | Element Should Contain | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][2] | General Usage
# Make sure editing again still works
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[1]/span | General Usage
|  | Wait Until Element Contains | xpath=//div[@id='tags_list']/div/div[1]/span//span[@class='tag-counter'] | 1
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2]/span | AI
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2]/span//span[@class='tag-counter'] | 1
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][1]
|  | Element Should Contain | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][1] | AI
|  | Element Should Be Visible | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][2]
|  | Element Should Contain | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][2] | General Usage
|  | Reload Page
|  | Click Element | id=fold_button
|  | Element Should Be Visible | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][1]
|  | Element Should Contain | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][1] | AI
|  | Element Should Be Visible | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][2]
|  | Element Should Contain | xpath=//div[@id='document_tags']//span[@class='tag tag-select'][2] | General Usage

| Tag search modal
|  | Sosse Go To | http://127.0.0.1/
|  | Element Should Be Visible | id=search_tags
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=tags_list
# Check counters
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[1] | General Usage
|  | Wait Until Element Contains | xpath=//div[@id='tags_list']/div/div[1]//span[@class='tag-counter'] | 1
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2] | AI
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2]//span[@class='tag-counter'] | 1
# Activate tags check
|  | ${tag_id}= | Get Element Attribute | xpath=//div[@id='tags_list']//span[@class='tag' and contains(., 'General Usage')] | id
|  | Click Element | xpath=//div[@id='tags_list']//span[@class='tag' and contains(., 'General Usage')]
|  | ${tag_pk}= | Replace String | ${tag_id} | tag- | ${EMPTY}
|  | Element Should Be Visible | xpath=//span[@id='tag-edit-${tag_pk}' and contains(., 'General Usage')]
|  | Click Element | id=tags_submit
# Search results
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/?tag=${tag_pk}&l=en&ps=20&c=1
|  | Element Should Be Visible | xpath=//div[@id='search_tags']//span[@id='tag-search-${tag_pk}' and contains(., 'General Usage')]
|  | Element Should Be Visible | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | ${results_count}= | Get Element Count | xpath=//div[@id='home-grid']/a
|  | Should Be Equal As Integers | ${results_count} | 1
# Reopen modal - Delete filter
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | Element Should Be Visible | xpath=//span[@id='tag-edit-${tag_pk}' and contains(., 'General Usage')]
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[1] | General Usage
|  | Wait Until Element Contains | xpath=//div[@id='tags_list']/div/div[1]//span[@class='tag-counter'] | 1
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2] | AI
|  | Element Should Contain | xpath=//div[@id='tags_list']/div/div[2]//span[@class='tag-counter'] | 1
|  | Element Should Be Visible | id=tag-edit-${tag_pk}
|  | Click Element | xpath=//span[@id='tag-edit-${tag_pk}']//a[@class='tag_delete']
|  | Element Should Not Be Visible | id=tag-edit-${tag_pk}
|  | Click Element | id=tags_submit
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/?l=en&ps=20&c=1

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
|  | Should Be Equal | ${loc} | http://127.0.0.1/?l=en&ps=20&c=1

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
|  | Should Be Equal | ${loc} | http://127.0.0.1/?l=en&ps=20&c=1

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
|  | Should Be Equal | ${loc} | http://127.0.0.1/?l=en&ps=20&c=1

| Admin - Tag link
|  | Sosse Go To | http://127.0.0.1/
|  | Click Element | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | Click Element | id=fold_button
|  | Click Element | xpath=//div[@id='top_bar_links']//a[contains(.,'Administration')]
|  | ${loc}= | Get Location
|  | Should Match Regexp | ${loc} | http://127.0.0.1/admin/se/document/[0-9]+/change/
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'][1]
|  | ${loc}= | Get Location
|  | Should Match Regexp | ${loc} | http://127.0.0.1/admin/se/tag/[0-9]+/change/
|  | Element Should Be Visible | xpath=//h4[contains(., 'General Usage')]

| Admin - Add tag to document
|  | Sosse Go To | http://127.0.0.1/
|  | Click Element | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | Click Element | id=fold_button
|  | Click Element | xpath=//div[@id='top_bar_links']//a[contains(.,'Administration')]
|  | ${loc}= | Get Location
|  | Should Match Regexp | ${loc} | http://127.0.0.1/admin/se/document/[0-9]+/change/
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | xpath=//span[@class='tag' and contains(., 'CPU')]
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 3
|  | Click Element | xpath=//button[contains(., 'Ok')]
|  | Wait Until Element Is Not Visible | id=tags
# Make sure editing again still works
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 3
|  | Click Element | xpath=//button[contains(., 'Ok')]
|  | Wait Until Element Is Not Visible | id=tags
# Check the updated tags on the admin change page
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 3
|  | Click Element | xpath=//input[@value='Save and continue editing']
|  | Wait Until Page Contains | You may edit it again below
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 3

| Admin - Remove tag from document
|  | Sosse Go To | http://127.0.0.1/
|  | Click Element | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | Click Element | id=fold_button
|  | Click Element | xpath=//div[@id='top_bar_links']//a[contains(.,'Administration')]
|  | ${loc}= | Get Location
|  | Should Match Regexp | ${loc} | http://127.0.0.1/admin/se/document/[0-9]+/change/
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 3
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 3
|  | Click Element | xpath=//span[@class='tag' and contains(., 'CPU')]
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | xpath=//button[contains(., 'Ok')]
|  | Wait Until Element Is Not Visible | id=tags
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | xpath=//input[@value='Save and continue editing']
|  | Wait Until Page Contains | You may edit it again below
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 2

| Admin - Clear tags
|  | Sosse Go To | http://127.0.0.1/
|  | Click Element | xpath=//div[contains(@class, 'res-home')][1]//h3
|  | Click Element | id=fold_button
|  | Click Element | xpath=//div[@id='top_bar_links']//a[contains(.,'Administration')]
|  | ${loc}= | Get Location
|  | Should Match Regexp | ${loc} | http://127.0.0.1/admin/se/document/[0-9]+/change/
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | id=clear_selected_tags
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 0
|  | Click Element | xpath=//button[contains(., 'Ok')]
|  | Wait Until Element Is Not Visible | id=tags
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 0
|  | Click Element | xpath=//input[@value='Save and continue editing']
|  | Wait Until Page Contains | You may edit it again below
|  | ${tags_count}= | Get Element Count | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Should Be Equal As Integers | ${tags_count} | 0

| Tag create search return url
|  | [Tags] | returnurl
|  | Sosse Go To | http://127.0.0.1/s/?q\=Test
|  | ${search_loc}= | Get Location
|  | Click Element | id=edit_search_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | Click Element | class=create-tag
|  | Input Text | id=id_name | Processing
|  | Click Element | xpath=//input[@value='Save']
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | ${search_loc}

| Tag create archive return url
|  | [Tags] | returnurl
|  | Sosse Go To | http://127.0.0.1/html/http://127.0.0.1/screenshots/website/index.html
|  | Click Element | id=fold_button
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | Click Element | class=create-tag
|  | Input Text | id=id_name | Processing2
|  | Click Element | xpath=//input[@value='Save']
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/html/http://127.0.0.1/screenshots/website/index.html

| Admin - Create Collection with tag
|  | Clear Collections
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/add/
|  | Input Text | id=id_name | Collection with Tag
|  | Input Text | id=id_unlimited_regex | http://example.com/.*
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | Click Element | xpath=//div[@id='tags_list']//span[@class='tag' and contains(., 'AI')]
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select']
|  | Element Should Contain | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'] | AI
|  | Click Element | xpath=//input[@value="Save"]
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/collection/
|  | ${active_tags}= | Get WebElement | xpath=//th[@class='field-name' and contains(., 'Collection with Tag')]/../td[@class='field-active_tags']
|  | Element Should Contain | ${active_tags} | AI

| Admin - Edit Collection with tag
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | Click Link | Collection with Tag
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 1
|  | Click Element | xpath=//div[@id='tags_list']//span[@class='tag' and contains(., 'General Usage')]
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'][1]
|  | Element Should Contain | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'][1] | AI
|  | Element Should Be Visible | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'][2]
|  | Element Should Contain | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'][2] | General Usage
# Make sure editing again still works
|  | Click Element | id=edit_tags
|  | Wait Until Element Is Visible | id=tags_list
|  | ${tags_count}= | Get Element Count | xpath=//div[@id='editing_tags']//span[@class='tag tag-select' and not(contains(@style, 'display: none'))]
|  | Should Be Equal As Integers | ${tags_count} | 2
|  | Click Element | id=tags_submit
|  | Wait Until Element Is Not Visible | id=tags
|  | Element Should Be Visible | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'][1]
|  | Element Should Contain | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'][1] | AI
|  | Element Should Be Visible | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'][2]
|  | Element Should Contain | xpath=//div[@class='form-row field-tags']//span[@class='tag tag-select'][2] | General Usage
|  | Click Element | xpath=//input[@value="Save"]
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/collection/
|  | ${tags_cell}= | Set Variable | //th[@class='field-name' and contains(., 'Collection with Tag')]/../td[@class='field-active_tags']
|  | Element Should Contain | xpath=${tags_cell}//span[@class='tag'][1] | AI
|  | Element Should Contain | xpath=${tags_cell}//span[@class='tag'][2] | General Usage
