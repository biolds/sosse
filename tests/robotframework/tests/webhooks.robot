| *Keywords* |

| Clear Webhooks
|  | Sosse Go To | http://127.0.0.1/admin/se/webhook/
|  | ${status} | ${has_docs}= | Run Keyword And Ignore Error | Element Text Should Not Be | id=changelist-form | 0 webhooks
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | id=action-toggle
|  | Run Keyword If | '${status}' == 'PASS' | Select From List By Label | xpath=//select[@name='action'] | Delete selected webhooks
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | xpath=//button[contains(., 'Go')]
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | xpath=//input[@type='submit']
