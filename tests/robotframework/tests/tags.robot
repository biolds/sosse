| *Keywords* |

| Create Tag | [Arguments] | ${name} | ${parent}=None
|  | Sosse Go To | http://127.0.0.1/admin/se/tag/add/
|  | Input Text | id=id_name | ${name}
|  | Run Keyword If | '${parent}' != 'None' | Select From List By Label | id=id__ref_node_id | ${parent}
|  | Click Element | xpath=//input[@value="Save"]

| Clear Tags
|  | Sosse Go To | http://127.0.0.1/admin/se/tag/
|  | ${status} | ${has_tags}= | Run Keyword And Ignore Error | Element Text Should Not Be | id=changelist-form | 0 tags
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | id=action-toggle
|  | Run Keyword If | '${status}' == 'PASS' | Select From List By Label | xpath=//select[@name='action'] | Delete selected tags
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | xpath=//button[contains(., 'Go')]
|  | Run Keyword If | '${status}' == 'PASS' | Click Element | xpath=//input[@type='submit']

| Create sample tags
|  | Clear Tags
|  | Create Tag | Hardware
|  | Create Tag | CPU | Hardware
|  | Create Tag | GPU | Hardware
|  | Create Tag | RAM | Hardware
|  | Create Tag | Storage | Hardware
|  | Create Tag | Motherboard | Hardware
|  | Create Tag | Power Supply | Hardware
|
|  | Create Tag | Software
|  | Create Tag | Operating System | Software
|  | Create Tag | Programming Languages | Software
|  | Create Tag | Development Tools | Software
|  | Create Tag | Security Software | Software
|
|  | Create Tag | Network & Connectivity
|  | Create Tag | Network Protocols | Network & Connectivity
|  | Create Tag | Internet Speed | Network & Connectivity
|  | Create Tag | WiFi Standards | Network & Connectivity
|
|  | Create Tag | Peripheral
|  | Create Tag | Keyboard | Peripheral
|  | Create Tag | Mouse | Peripheral
|  | Create Tag | Monitor | Peripheral
|
|  | Create Tag | General Usage
|  | Create Tag | Gaming PC | General Usage
|  | Create Tag | Workstation Build | General Usage
|  | Create Tag | AI | General Usage
|  | Create Tag | Budget Laptop | General Usage
|  | Create Tag | Custom PC Build | General Usage
