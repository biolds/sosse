| *Settings* |
| Library | SeleniumLibrary
| Library | VRT
| Resource | ../tests/common.robot

| *Keywords* |
| VRT check | [Arguments] | ${name}
|  | Capture Page Screenshot | vrt.png
|  | Screenshot Should Match Baseline | ${name} | screenshots/vrt.png | 0 | firefox | 1024x768

| *Test Cases* |
| Admin UI access
|  | Start

| Crawl a new URL
|  | Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_url
|  | Input Text | id=id_url | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Wait Until Page Contains | Create a new policy
|  | VRT check | New policy
|  | Click Element | xpath=//input[@value='Confirm']
|  | Wait Until Page Contains | Crawl status
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_status/
|  | Page Should Not Contain | No crawlers running.
|  | Page Should Not Contain | exited
|  | Wait Until Page Contains | 4 recurring documents | 2min
|  | Wait Until Page Contains | 0 pending documents | 2min
|  | Page Should Contain | idle
|  | Reload Page
|  | Wait Until Page Contains | Crawl status
|  | Scroll To Bottom
|  | VRT check | Crawl status

| Home
|  | Go To | http://127.0.0.1/
|  | VRT check | Home
|  | Click Element | id=user_menu_button
|  | VRT check | Home - user menu
|  | Reload Page
|  | Click Element | id=conf_menu_button
|  | VRT check | Home - conf menu
|  | Click Element | id=more
|  | Click Element | xpath=//div[@id="adv_search1"]/input[1]
|  | VRT check | Home - search params

| Search
|  | Go To | http://127.0.0.1/
|  | Wait Until Element Is Visible | id=id_q
|  | Input Text | id_q | website
|  | Click Button | search_button
|  | Wait Until Page Contains | 4 sites found
|  | VRT check | Home - search

| Login page
|  | Go To | http://127.0.0.1/logout/
|  | VRT check | Login
|  | Login

| Simple pages
|  | Go To | http://127.0.0.1/prefs/
|  | VRT check | Preferences
|  | Go To | http://127.0.0.1/history/
|  | VRT check | History
|  | Go To | http://127.0.0.1/admin/password_change/
|  | VRT check | Password change
|  | Go To | http://127.0.0.1/about/
|  | VRT check | About
|  | Go To | http://127.0.0.1/stats/
|  | Wait Until Element Is Not Visible | class=loader
|  | Sleep | 5s
|  | VRT check | Stats

| Admin pages
|  | Go To | http://127.0.0.1/admin/
|  | VRT check | Admin
|  | Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | VRT check | Admin - list view
|  | Go To | http://127.0.0.1/admin/se/crawlpolicy/1/change/
|  | VRT check | Admin - edit view
|  | Go To | http://127.0.0.1/admin/auth/user/1/delete/
|  | VRT check | Admin - delete view

| Cache
|  | Go To | http://127.0.0.1/screenshot/http://127.0.0.1/screenshots/website/index.html
|  | VRT check | Cache
|  | Click Element | id=fold_button
|  | VRT check | Cache - Panel
|  | Go To | http://127.0.0.1/www/http://127.0.0.1/screenshots/website/index.html
|  | VRT check | Cache - Text
|  | Go To | http://127.0.0.1/words/http://127.0.0.1/screenshots/website/index.html
|  | VRT check | Cache - Words
|  | Stop

