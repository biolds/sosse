| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Suite Setup | Setup
| Suite Teardown | Close All Browsers

| *Keywords* |
| Setup
|  | Login
|  | Execute Javascript | window.onerror = function(errorMessage) { dialog(errorMessage); }
