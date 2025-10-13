| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot
| Resource | ../tests/collection.robot
| Resource | ../tests/documents.robot
| Resource | ../tests/webhooks.robot
| Suite Setup | Setup
| Suite Teardown | Tear Down

| *Keywords* |
| Setup
|  | Set Selenium Timeout | 1 min
|  | Login
|  | Execute Javascript | window.onerror = function(errorMessage) { dialog(errorMessage); }
|  | Clear Documents
|  | Clear Collections
|  | Clear webhooks
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.cookie import Cookie ; Cookie.objects.all().delete()
|  | Run Command | ${SOSSE_ADMIN} | shell | -c | from se.domain import Domain ; Domain.objects.all().delete()

| Tear Down
|  | Capture Page Screenshot
|  | Close All Browsers
