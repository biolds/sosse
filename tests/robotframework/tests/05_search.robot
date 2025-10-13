| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot
| Resource | profile.robot
| Resource | documents.robot
| Test Setup | Clear Documents

| *Test Cases* |
| Search links
# Link to archive
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../home_favicon.json | shell=True
|  | Load Data With Collection | ${CURDIR}/../home_docs.json
|  | Profile set search links to archive
|  | Sosse Go To | http://127.0.0.1/
|  | Wait Until Element Is Visible | id=id_q
|  | Element Text Should Be | xpath=//div[@id='home-grid']/a[1] | Cypress Documentation
|  | ${href}= | Get Element Attribute | xpath=//div[@id='home-grid']/a[1] | href
|  | Should Be Equal | ${href} | http://127.0.0.1/archive/https://docs.cypress.io/

# Link to source
|  | Profile set search links to source url
|  | Sosse Go To | http://127.0.0.1/
|  | Wait Until Element Is Visible | id=id_q
|  | Element Text Should Be | xpath=//div[@id='home-grid']/a[1] | Cypress Documentation
|  | ${href}= | Get Element Attribute | xpath=//div[@id='home-grid']/a[1] | href
|  | Should Be Equal | ${href} | https://docs.cypress.io/
