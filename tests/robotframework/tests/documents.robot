| *Settings* |
| Library | OperatingSystem
| Resource | collection.robot
| Resource | crawl_queue.robot

| *Keywords* |
| Clear Documents
|  | Sosse Go To | http://127.0.0.1/admin/se/document/
|  | ${status} | ${has_docs}= | Run Keyword And Ignore Error | Element Text Should Not Be | id=changelist-form | 0 documents
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | id=action-toggle
|  | Run Keyword If | '${status}' == 'PASS' | Select From List By Label | xpath=//select[@name='action'] | Delete selected documents
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | xpath=//button[contains(., 'Go')]
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | xpath=//input[@type='submit']

| Load Data With Collection | [Arguments] | ${json_file}
|  | ${collection_id}= | Get Default Collection Id
|  | ${temp_file}= | Evaluate | os.path.abspath(tempfile.mktemp(suffix='.json')) | modules=tempfile,os
|  | Run Command | bash | -c | jq 'map(if .model \=\= "se.document" then .fields.collection \= ${collection_id} else . end)' ${json_file} > ${temp_file} | shell=True
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${temp_file} | shell=True
|  | Remove File | ${temp_file}

| Crawl Test Website
|  | Clear Collections
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | Click Link | Default
|  | Wait Until Element Is Visible | id=id_unlimited_regex
|  | Input Text | id=id_unlimited_regex | http://127.0.0.1/screenshots/website/.*
|  | Click Link | 🌍 Browser
|  | Select From List By Label | id=id_default_browse_mode | Chromium
|  | Click Element | id=id_take_screenshots
|  | Click Element | xpath=//input[@value="Save"]
|  | Sosse Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_urls
|  | Input Text | id=id_urls | http://127.0.0.1/screenshots/website/index.html${\n}http://127.0.0.1/static/Cat%20photos.zip
|  | Click Element | xpath=//input[@value='Add to Crawl Queue']
|  | Sosse Wait Until Page Contains | 2 URLs were queued
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Wait For Queue | 1
