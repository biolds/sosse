| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Suite Setup | Setup
| Suite Teardown | Close All Browsers

| *Keywords* |
| Setup
|  | Set Selenium Timeout | 1 min
|  | Login
|  | Execute Javascript | window.onerror = function(errorMessage) { dialog(errorMessage); }
