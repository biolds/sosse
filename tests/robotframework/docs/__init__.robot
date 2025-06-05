| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Suite Setup | Setup
| Suite Teardown | Tear Down

| *Keywords* |
| Setup
|  | Set Selenium Timeout | 1 min
|  | Login
|  | Execute Javascript | window.onerror = function(errorMessage) { dialog(errorMessage); }

| Tear Down
|  | Capture Page Screenshot
|  | Close All Browsers
