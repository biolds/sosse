| *Settings* |
| Library | SeleniumLibrary
| Library | VRT
| Resource | ../tests/common.robot
| Suite Setup | Setup
| Suite Teardown | Close All Browsers

| *Keywords* |
| Setup
|  | Login
|  | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../fixtures.json | shell=True
