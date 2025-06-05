| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot

| *Test Cases* |
| Search website
|  | Sosse Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Input Text | id=id_url_regex | https://example.com/
|  | Sosse Capture Page Screenshot | guide_search_policy.png
