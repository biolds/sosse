| *Settings* |
| Library | Process

| *Keywords* |
| Login
|  | Open Browser | http://127.0.0.1/ | browser=Firefox |  options=add_argument("--headless")
#|  | Open Browser | http://127.0.0.1/ | browser=Chrome | options=add_argument("--no-sandbox");options=add_argument("--disable-dev-shm-usage");add_argument("--headless");add_argument('--enable-precise-memory-info');add_argument('--disable-default-apps')
|  | Set Window Size | 1024 | 768
|  | Set Screenshot Directory | screenshots/
|  | Input Text | id=id_username | admin
|  | Input Text | id=id_password | admin
|  | Click Element | xpath=//form[@id='login-form']//input[@type='submit']
|  | Wait Until Element Contains | id=menu_username | admin


| Hilight | [Arguments] | @{kwargs}
|  | Wait Until element Is Visible | @{kwargs}
|  | ${elem}= | Get WebElement | @{kwargs}
|  | Execute Javascript | arguments[0].style = 'box-shadow: 0px 0px 4px 4px #91ffba; margin: 5px; padding: 4px 8px 0px 8px;' | ARGUMENTS | ${elem}

| Scroll To Elem | [Arguments] | @{kwargs}
|  | Wait Until element Is Visible | @{kwargs}
|  | ${elem}= | Get WebElement | @{kwargs}
|  | Execute Javascript | window.scroll(0, 0)
|  | Execute Javascript | window.scroll(0, arguments[0].getBoundingClientRect().top - 10) | ARGUMENTS | ${elem}

| Scroll To Bottom
|  | Execute Javascript | window.scroll(0, 0)
|  | Execute Javascript | window.scroll(0, document.body.scrollHeight)

| Run Command | [Arguments] | @{args} | &{kwargs}
|  | ${ret}= | Run Process | @{args} | &{kwargs}
|  | Log | ${ret.stdout}
|  | Log | ${ret.stderr}
|  | Should Be Equal As Numbers | ${ret.rc} | 0
|  | RETURN | ${ret}

| Sosse Go To | [Arguments] | @{args} | &{kwargs} |
| | Page Should Not Contain | Traceback |
| | Go To | @{args} | &{kwargs} |

| Sosse Wait Until Page Contains | [Arguments] | @{args} | &{kwargs} |
| | Page Should Not Contain | Traceback |
| | Wait Until Page Contains | @{args} | &{kwargs} |

| Sosse Capture Page Screenshot |
| | [Arguments] | @{args} | &{kwargs} |
| | Page Should Not Contain | Traceback |
| | Page Should Not Contain | Page not found |
| | Capture Page Screenshot | @{args} | &{kwargs} |
