| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot
| Resource | collection.robot
| Resource | documents.robot
| Resource | crawl_queue.robot
| Test Setup | Setup For Collection Tests

| *Keywords* |
| Setup For Collection Tests
|  | Clear Collections
|  | Clear Documents

| *Test Cases* |
| Duplicate Collection
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | Element Should Be Visible | xpath=//p[@class='paginator' and contains(., '1 collection')]
|  | Click Element | id=action-toggle
|  | Select From List By Label | xpath=//select[@name='action'] | Duplicate
|  | Click Element | xpath=//button[text()='Go']
|  | Element Should Be Visible | xpath=//p[@class='paginator' and contains(., '2 collections')]
|  | Click Link | Copy of Default
|

| Move Documents To Collection
|  | # Create test documents in Default collection first
|  | Crawl Test Website
|  |
|  | # Create a second collection for testing
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/add/
|  | Input Text | id=id_name | Target Collection
|  | Input Text | id=id_unlimited_regex | .*
|  | Click Element | xpath=//input[@value="Save"]
|  |
|  | # Go to documents admin page
|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  |
|  | # Select first two documents
|  | Click Element | xpath=(//input[@type='checkbox' and @name='_selected_action'])[1]
|  | Click Element | xpath=(//input[@type='checkbox' and @name='_selected_action'])[2]
|  |
|  | # Use Move to collection action
|  | Select From List By Label | xpath=//select[@name='action'] | Move to collection
|  | Click Element | xpath=//button[text()='Go']
|  |
|  | # Should be redirected to move to collection page
|  | Wait Until Page Contains | Move to Collection
|  | Wait Until Page Contains | Move 2 documents to collection
|  |
|  | # Select target collection
|  | Select From List By Label | id=id_collection | Target Collection
|  | Click Element | xpath=//input[@value='Move Documents']
|  |
|  | # Should be back on documents page with success message
|  | Wait Until Page Contains | 2 documents moved to collection 'Target Collection'
|  |
|  | # Verify documents are now showing Target Collection
|  | Page Should Contain | Target Collection
