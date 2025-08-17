| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot
| Resource | collection.robot
| Test Setup | Clear Collections

| *Test Cases* |
| Duplicate policy
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | Element Should Be Visible | xpath=//p[@class='paginator' and contains(., '1 Collection')]
|  | Click Element | id=action-toggle
|  | Select From List By Label | xpath=//select[@name='action'] | Duplicate
|  | Click Element | xpath=//button[text()='Go']
|  | Element Should Be Visible | xpath=//p[@class='paginator' and contains(., '2 Collections')]
|  | Click Link | Copy of (default)
