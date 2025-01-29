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

SOSSE (Selenium Open Source Search Engine) is a web archiving software, crawler, and search engine. It’s hosted on both
[GitLab](https://gitlab.com/biolds1/sosse) and [GitHub](https://github.com/biolds/sosse). Feel free to use either platform to
submit feature requests, bug reports, merge requests, or [start a discussion](https://github.com/biolds/sosse/discussions).

## Key Features

- 🌍 **Web Page Search**: Search the content of web pages, including dynamically rendered ones, with advanced queries.
  ([doc](https://sosse.readthedocs.io/en/stable/guides/search.html))

- 🕑 **Recurring Crawling**: Crawl pages at fixed intervals or adapt the rate based on content changes.
  ([doc](https://sosse.readthedocs.io/en/stable/crawl/policies.html))

- 🔖 **Web Page Archiving**: Archive HTML content, adjust links for local use, download required assets, and support
  dynamic content. ([doc](https://sosse.readthedocs.io/en/stable/guides/archive.html))

- 📂 **File Downloads**: Batch download binary files from web pages.
  ([doc](https://sosse.readthedocs.io/en/stable/guides/download.html))

- 🔔 **Atom Feeds**: Generate content feeds for websites that don’t have them, or receive updates when a new page
  containing a keyword is published.
  ([doc](https://sosse.readthedocs.io/en/stable/guides/feed_website_monitor.html))

- 🔒 **Authentication**: The crawler can authenticate to access private pages and retrieve content.
  ([doc](https://sosse.readthedocs.io/en/stable/guides/authentication.html))

- 👥 **Permissions**: Admins can configure crawlers and view statistics, while authenticated users can search or do so anonymously.
  ([doc](https://sosse.readthedocs.io/en/stable/permissions.html))

- 👤 **Search Features**: Includes private search history ([doc](https://sosse.readthedocs.io/en/stable/user/history.html)),
  and external search engine shortcuts ([doc](https://sosse.readthedocs.io/en/stable/user/shortcuts.html)), etc.

Explore the 📚 [documentation](https://sosse.readthedocs.io/en/stable/index.html) and check out some
📷 [screenshots](https://sosse.readthedocs.io/en/stable/screenshots.html).

SOSSE is written in Python and is distributed under the [GNU AGPLv3 license](https://www.gnu.org/licenses/agpl-3.0.en.html). It uses browser-based crawling with [Mozilla Firefox](https://www.mozilla.org/firefox/) or
[Google Chromium](https://www.chromium.org/Home) alongside [Selenium](https://www.selenium.dev/) to index pages that rely on JavaScript. For faster crawling, [Requests](https://docs.python-requests.org/en/latest/index.html) can also be used. SOSSE is lightweight and uses
[PostgreSQL](https://www.postgresql.org/) for data storage.

## Try It Out

To quickly try the latest version with Docker:

```
docker run -p 8005:80 biolds/sosse:latest
```

Then, open [http://127.0.0.1:8005/](http://127.0.0.1:8005/) and log in with the username `admin` and password `admin`.

For persistence of Docker data or alternative installation methods, please refer to the [installation guide](https://sosse.readthedocs.io/en/stable/install.html).

## Stay Connected

Join the [Discord server](https://discord.gg/Vt9cMf7BGK) to get help, share ideas, or discuss SOSSE!
