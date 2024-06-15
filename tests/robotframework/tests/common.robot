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
|  | Wait Until Element Is Visible | id=menu_username


| Hilight | [Arguments] | @{kwargs}
|  | Wait Until element Is Visible | @{kwargs}
|  | ${elem}= | Get WebElement | @{kwargs}
|  | Execute Javascript | arguments[0].style = 'box-shadow: 0px 0px 4px 4px #91ffba; margin: -4px 0px 0px -2px; padding: 4px 8px 0px 8px;' | ARGUMENTS | ${elem}

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
