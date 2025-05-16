| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot
| Resource | crawl_policy.robot
| Test Setup | Clear Crawl Policies

| *Test Cases* |
| Duplicate policy
|  | Sosse Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | Element Should Be Visible | xpath=//p[@class='paginator' and contains(., '1 Crawl Policy')]
|  | Click Element | id=action-toggle
|  | Select From List By Label | xpath=//select[@name='action'] | Duplicate
|  | Click Element | xpath=//button[text()='Go']
|  | Element Should Be Visible | xpath=//p[@class='paginator' and contains(., '2 Crawl Policies')]
|  | Click Link | Copy of (default)
