Guidelines for Ethical Use
==========================

When using a web crawler or scraper, it’s important to be responsible and ethical. Here are some quick tips to keep in
mind:

Get Permission First
--------------------

Before crawling a site, make sure you’re allowed to access it. Although your crawler may have the ability to ignore
`robots.txt` or modify the `User-Agent`, **always respect the site owner’s preferences**:

- Read the site’s terms of service to see if scraping is allowed.
- If you’re unsure, consider reaching out to the site owner for permission.

Crawl Responsibly & Respect the Environment
-------------------------------------------

Crawling can impact both website performance and the environment. Here’s how to do it responsibly:
- **Avoid Overloading Servers**: Don’t make too many requests at once or crawl the same pages repeatedly.

- **Use Data Dumps**: If available, use downloadable data dumps (e.g., `Kiwix <https://www.kiwix.org/>`_)
  instead of crawling, which helps reduce server load and saves resources.

- **Consider Environmental Impact**: Crawling consumes energy. Keep your crawls efficient—only collect the data you
  need, and avoid unnecessary large downloads like media files.

- **Use APIs When Available**: If the website provides an API, prefer using it instead of crawling, as APIs are
  optimized for data access and reduce server load.

- **Prefer Generating Scripts with AI**: When possible, use AI to generate scripts for structured data extraction
  rather than parsing unstructured pages, which can be less efficient and error-prone.

Respect the Web
---------------

Ethical scraping is all about respect:

- Be transparent and let site owners know if you're crawling their content.
- Avoid scraping personal or sensitive information unless explicitly allowed.
- Follow copyright laws and properly attribute sources.
- Use scraping tools with the right intent — to learn, build, and contribute, not to exploit or deceive.

For more information, see `Is Web Scraping Legal? <https://webscraping.fyi/legal/>`_.
