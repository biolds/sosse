| *Keywords* |

| Profile set search links to archive
|  | SOSSE Go To | http://127.0.0.1/profile/
|  | Select Checkbox | id=archive_links
|  | Click Element | //button[contains(text(),'Save')]
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/
