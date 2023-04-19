| *Keywords* |
| Hilight | [Arguments] | @{kwargs}
|  | Wait Until element Is Visible | @{kwargs}
|  | ${elem}= | Get WebElement | @{kwargs}
|  | Execute Javascript | arguments[0].style = 'box-shadow: 0px 0px 4px 4px #91ffba; margin: -4px 0px 0px -2px; padding: 4px 8px 4px 8px;' | ARGUMENTS | ${elem}

| Scroll To Elem | [Arguments] | @{kwargs}
|  | Wait Until element Is Visible | @{kwargs}
|  | ${elem}= | Get WebElement | @{kwargs}
|  | Execute Javascript | window.scroll(0, 0)
|  | Execute Javascript | window.scroll(0, arguments[0].getBoundingClientRect().top - 10) | ARGUMENTS | ${elem}
un
