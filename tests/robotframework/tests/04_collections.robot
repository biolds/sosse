| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot
| Resource | collection.robot
| Test Setup | Clear Collections

| *Test Cases* |
| Duplicate Collection
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/
|  | Element Should Be Visible | xpath=//p[@class='paginator' and contains(., '1 collection')]
|  | Click Element | id=action-toggle
|  | Select From List By Label | xpath=//select[@name='action'] | Duplicate
|  | Click Element | xpath=//button[text()='Go']
|  | Element Should Be Visible | xpath=//p[@class='paginator' and contains(., '2 collections')]
|  | Click Link | Copy of Default
