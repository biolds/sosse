| *Keywords* |

| Wait For Queue | [Arguments] | ${expected_count}
|  | Sosse Wait Until Page Contains | Crawl queue
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_queue/
|  | Page Should Not Contain | No crawlers running.
|  | Page Should Not Contain | exited
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_pending_count" and contains(., '0')] | 2min
|  | Wait Until Element Is Visible | xpath=//div[@id="queue_new_count" and contains(., '0')] | 2min
|  | ${doc_count}= | Get Element Count | xpath=//table[@id="result_list"]//tr
|  | ${error_count}= | Get Element Count | xpath=//table[@id="result_list"]//tr/td[4]/img[@src="/static/admin/img/icon-no.svg"]
|  | Should Be Equal As Integers | ${error_count} | 0 | Found error status indicators in crawl queue
