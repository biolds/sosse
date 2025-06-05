| *Settings* |
| Library | SeleniumLibrary
| Library | String
| Resource | common.robot
| Resource | webhooks.robot

| *Test Cases* |
| Trigger non-saved webhook
|  | Clear Webhooks
|  | Sosse Go To | http://127.0.0.1/admin/se/webhook/add/
|  | Input Text | id=id_name | Test webhook
|  | Element Should Not Be Visible | id=webhook_test_result
|  | Click Element | id=webhook_test_button
|  | Wait Until Element Is Visible | id=webhook_test_result
|  | Wait Until Element Contains | id=webhook_test_result | Webhook configuration error
|  | Input Text | id=id_url | http://127.0.0.1:8000/post
|  | Click Element | id=webhook_test_button
|  | Wait Until Element Contains | id=webhook_test_result | 200 OK

| Trigger saved webhook
|  | Clear Webhooks
|  | Sosse Go To | http://127.0.0.1/admin/se/webhook/add/
|  | Input Text | id=id_name | Test webhook
|  | Input Text | id=id_url | http://127.0.0.1:8000/post
|  | Click Element | xpath=//input[@value="Save"]
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/webhook/
|  | Click Link | Test webhook
|  | Element Should Not Be Visible | id=webhook_test_result
|  | Click Element | id=webhook_test_button
|  | Wait Until Element Is Visible | id=webhook_test_result
|  | Wait Until Element Contains | id=webhook_test_result | 200 OK
