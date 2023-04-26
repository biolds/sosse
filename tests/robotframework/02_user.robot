| *Settings* |
| Library | SeleniumLibrary
| Library | Process
| Resource | common.robot

| *Test Cases* |
| Login
|  | Login
|  | Input Text | id_q | website
|  | Click Button | search_button
|  | Wait Until Page Contains | 4 results
|  | ${res_count}= | Get Element Count | xpath=//div[@class='res']
|  | Should Be Equal As Numbers | ${res_count} | 4
|  | Capture Page Screenshot | search.png

| Preferences
|  | Click Button | id=user_menu_button
|  | Click Link | Preferences
|  | Wait Until Page Contains | Search terms parsing language
|  | Capture Page Screenshot | preferences.png
