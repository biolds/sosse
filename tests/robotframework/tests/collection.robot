| *Keywords* |

| Clear Collections
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | ${status} | ${has_docs}= | Run Keyword And Ignore Error | Element Text Should Be | id=changelist-form | 0 Collections
|  | Return From Keyword If | '${status}' == 'PASS'
|  | ${status} | ${has_docs}= | Run Keyword And Ignore Error | Element Text Should Not Be | id=changelist-form | 1 Collection
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | id=action-toggle
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | xpath=//td[@class='action-checkbox']/input
|  | Run Keyword If | '${status}' == 'PASS' | Select From List By Label | xpath=//select[@name='action'] | Delete selected Collections
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | xpath=//button[contains(., 'Go')]
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | xpath=//input[@type='submit']
