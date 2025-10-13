| *Keywords* |

| Clear Collections
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | ${status} | ${has_docs}= | Run Keyword And Ignore Error | Element Text Should Be | id=changelist-form | 1 Collection
|  | Return From Keyword If | '${status}' == 'PASS'
|  | Click Element | id=action-toggle
|  | Select From List By Label | xpath=//select[@name='action'] | Delete selected collections
|  | Click Element | xpath=//button[contains(., 'Go')]
|  | Click Element | xpath=//input[@type='submit']

| Get Default Collection Id
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | ${default_link}= | Get Element Attribute | xpath=//a[contains(text(), 'Default')] | href
|  | ${collection_id}= | Evaluate | '${default_link}'.split('/')[-3]
|  | RETURN | ${collection_id}
