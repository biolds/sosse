| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot
| Suite Setup | Setup
| Suite Teardown | Close All Browsers

| *Keywords* |
| Setup
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../fixtures.json | shell=True
|  | Login
|  | Execute Javascript | window.onerror = function(errorMessage) { dialog(errorMessage); }
