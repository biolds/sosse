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
|  | Click Element | id=more
|  | Select From List By Value | id=doc_lang | en
|  | Input Text | xpath=//input[@name='fv1'] | cats
|  | Click Element | xpath=//div[@id='adv_search1']/input[@value='+']
|  | Select From List By Label | xpath=//select[@name='ft2'] | Exclude
|  | Select From List By Label | xpath=//select[@name='ff2'] | Mimetype
|  | Select From List By Label | xpath=//select[@name='fo2'] | Matching Regexp
|  | Input Text | xpath=//input[@name='fv2'] | text/markdown
|  | Capture Element Screenshot | id=adv_search | extended_search.png
|  | Capture Element Screenshot | xpath=//div[@id='adv_search2']/input[@value='+'] | extended_search_plus_button.png
|  | Capture Element Screenshot | xpath=//div[@class='res'][2] | search_result.png
|  | Capture Element Screenshot | id=stats_button | stats_button.png
|  | Capture Element Screenshot | id=atom_button | atom_button.png
|  | Click Element | id=stats_button
|  | Capture Element Screenshot | id=word_stats | word_stats.png

| Preferences
|  | Click Button | id=user_menu_button
|  | Click Link | Preferences
|  | Wait Until Page Contains | Search terms parsing language
|  | Capture Page Screenshot | preferences.png
