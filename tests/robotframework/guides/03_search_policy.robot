| *Settings* |
| Library | SeleniumLibrary
| Resource | ../tests/common.robot

| *Test Cases* |
| Search website
|  | Sosse Go To | http://127.0.0.1/admin/se/collection/add/
|  | Input Text | id=id_name | Example Collection
|  | Input Text | id=id_unlimited_regex | https://example.com/
|  | Sosse Capture Page Screenshot | guide_search_collection.png
