<p>
  <img src="https://raw.githubusercontent.com/biolds/sosse/main/se/static/se/logo.svg" width="64" align="right">
  <a href="https://gitlab.com/biolds1/sosse/" alt="Gitlab code coverage" style="text-decoration: none">
    <img src="https://img.shields.io/gitlab/pipeline-coverage/biolds1/sosse?branch=main&style=flat-square">
  </a>
  <a href="https://gitlab.com/biolds1/sosse/-/pipelines" alt="Gitlab pipeline status" style="text-decoration: none">
    <img src="https://img.shields.io/gitlab/pipeline-status/biolds1/sosse?branch=main&style=flat-square">
  </a>
  <a href="https://sosse.readthedocs.io/en/stable/" alt="Documentation" style="text-decoration: none">
    <img src="https://img.shields.io/readthedocs/sosse?style=flat-square">
  </a>
  <a href="https://discord.gg/Vt9cMf7BGK" alt="Discord" style="text-decoration: none">
    <img src="https://img.shields.io/discord/1102142186423844944?style=flat-square&color=%235865f2">
  </a>
  <a href="https://gitlab.com/biolds1/sosse/-/blob/main/LICENSE" alt="License" style="text-decoration: none">
    <img src="https://img.shields.io/gitlab/license/biolds1/sosse?style=flat-square">
  </a>
</p>

# SOSSE 🦦

SOSSE (Selenium Open Source Search Engine) is a Web archiving software, crawler and search engine. It is hosted on both
[Gitlab](https://gitlab.com/biolds1/sosse) and [Github](https://github.com/biolds/sosse) site, please use any of them to
open feature requests, bug report or merge requests, or [open a discussion](https://github.com/biolds/sosse/discussions).

SOSSE main features are:

- 🌍 Web pages search: The text content of web pages, including complex, dynamically rendered pages, is searchable with
  advanced queries.
- 🕑 Recurring crawling: Pages can be crawled at fixed intervals or at an adaptive rate based on how often they change.
- 📂 File downloads: Binary files can be batch downloaded from web pages.
- 🔖 Web page archiving: Web pages can be saved for offline browsing.
- 🔔 Atom feeds: Notifications are provided when a new page with a keyword appears, and content feeds can be generated
  for websites that don't have them.
- 🔒 Authentication: The crawler can authenticate to access private pages and retrieve content.
- 👥 Permissions: Admins can configure crawlers and view stats, while authenticated users can search or do so
  anonymously.
- 👤 Search features: search history, shortcut search queries...

See the [documentation](https://sosse.readthedocs.io/en/stable/) and
[screenshots](https://sosse.readthedocs.io/en/stable/screenshots.html).

SOSSE is written in Python and distributed under the [GNU-AGPLv3 license](https://www.gnu.org/licenses/agpl-3.0.en.html).
It utilizes browser-based crawling with [Mozilla Firefox](https://www.mozilla.org/firefox/) or
[Google Chromium](https://www.chromium.org/Home) alongside [Selenium](https://www.selenium.dev/) to index pages that
use JavaScript. For faster crawling, [Requests](https://docs.python-requests.org/en/latest/index.html) can also be used.
SOSSE has low resource requirements, as it is entirely written in Python and employs
[PostgreSQL](https://www.postgresql.org/) for data storage.

# Try it out

You can try the latest version with Docker:

```
docker run -p 8005:80 biolds/sosse:latest
```

Open http://127.0.0.1:8005/, and log in with user `admin`, password `admin`.

To persist Docker data, or find alternative installation methods, please check the [documentation](https://sosse.readthedocs.io/en/stable/install.html).

# Keep in touch

Join the [Discord server](https://discord.gg/Vt9cMf7BGK) to get help and share ideas!
