![Gitlab code coverage](https://img.shields.io/gitlab/pipeline-coverage/biolds1/sosse?branch=main&style=flat-square)
![Gitlab pipeline status](https://img.shields.io/gitlab/pipeline-status/biolds1/sosse?branch=main&style=flat-square)
![GitLab](https://img.shields.io/gitlab/license/biolds1/sosse?style=flat-square)

SOSSE
=====

SOSSE (Selenium Open Source Search Engine) is a search engine and crawler written in Python, distributed under the [GNU-AGPLv3 license](https://www.gnu.org/licenses/agpl-3.0.en.html). It is hosted on both [Gitlab](https://gitlab.com/biolds1/sosse) and [Github](https://github.com/biolds/sosse) site, please use any of them to open feature requests, bug report or merge requests, or [open a discussion](https://github.com/biolds/sosse/discussions).

SOSSE main features are:
- 🌍 Browser based crawling: the crawler can use [Google Chromium](https://www.chromium.org/Home) and [Selenium](https://www.selenium.dev/) to index pages that use Javascript. [Requests](https://docs.python-requests.org/en/latest/index.html) can also be used for faster crawling
- 🏖 Low resources requirements: SOSSE is entirely written in Python and uses [PostgreSQL](https://www.postgresql.org/) for data storage
- 🖼 Offline cache: SOSSE can take screenshots of crawled pages and make them browsable offline
- 🔓 Authentication: the crawlers can submit authentication forms with provided credentials
- 🔗 Search engines shortcuts: shortcuts search queries can be used to redirect to external search engines (also called "bang" searches)
- 🔖 Search history: users can authenticate to log their search query history
