| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot

| *Test Cases* |
| Search website
|  | SOSSE Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Input Text | id=id_url_regex | https://example.com/
|  | SOSSE Capture Page Screenshot | guide_search_policy.png
