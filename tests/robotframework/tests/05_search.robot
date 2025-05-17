| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot
| Resource | profile.robot

| *Test Cases* |
| Search links to archive
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../home_favicon.json | shell=True
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../home_docs.json | shell=True
|  | Profile set search links to archive
|  | Sosse Go To | http://127.0.0.1/
|  | Wait Until Element Is Visible | id=id_q
|  | Element Text Should Be | xpath=//div[@id='home-grid']/a[1] | Cypress Documentation
|  | ${href}= | Get Element Attribute | xpath=//div[@id='home-grid']/a[1] | href
|  | Should Be Equal | ${href} | http://127.0.0.1/archive/https://docs.cypress.io/

| Search links to source site
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../home_favicon.json | shell=True
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../home_docs.json | shell=True
|  | Profile set search links to source url
|  | Sosse Go To | http://127.0.0.1/
|  | Wait Until Element Is Visible | id=id_q
|  | Element Text Should Be | xpath=//div[@id='home-grid']/a[1] | Cypress Documentation
|  | ${href}= | Get Element Attribute | xpath=//div[@id='home-grid']/a[1] | href
|  | Should Be Equal | ${href} | https://docs.cypress.io/
