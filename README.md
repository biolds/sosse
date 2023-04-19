SOSSE (Selenium Open Source Search Engine) is a search engine and crawler written in Python, distributed under the [GNU-AGPLv3 license](https://www.gnu.org/licenses/agpl-3.0.en.html).

It's main few features are:
- Browser based crawling: the crawler can use [Google Chromium](https://www.chromium.org/Home) and [Selenium](https://www.selenium.dev/)
ndex pages that use Javascript. [Requests](https://docs.python-requests.org/en/latest/index.html) can also be used for faster crawling
- Low resources requirements: SOSSE is entirely written in Python and uses [PostreSGL](https://www.postgresql.org/) for data storage
- Offline cache: SOSSE can take screenshots of crawled pages and make them browsable offline
- Authentication: the crawlers can submit authentication forms with provided credentials
- Bang searches: shortcuts search queries can be used to redirect to external search engines
- Search history: users can authenticate to have their search query history saved

apt update
apt install python3-django/bullseye-backports python3-requests python3-bs4 python3-html5lib python3-psycopg2 python3-django-uwsgi python3-langdetect python3-pygal python3-magic python3-defusedxml python3-selenium libjs-jquery postgresql nginx uwsgi chromium chromium-driver

su postgres -c "psql --command \"CREATE USER django WITH SUPERUSER PASSWORD 'password'\""
su postgres -c "psql --command \"CREATE DATABASE django OWNER django\""

In settings.py:

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'django',
        'USER': 'django',
        'PASSWORD': 'password',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

Change SECRET_KEY and ALLOWED_HOSTS

./manage.py collectstatic
./manage.py createsuperuser
./manage.py loaddata se.json

Adding an OpenSearch search engine:
./manage.py load_se opensearch.xml

Adding a language:
- check/add support for the language detection in Langdetect (https://pypi.org/project/langdetect/)
- check/add support for the language in postgresql (https://www.postgresql.org/docs/current/textsearch-dictionaries.html)
- add the new entry to the SOSSE_LANGDETECT_TO_POSTGRES option, where the key is ISO 639-1 code for this language,
  and the value, the name of the language as stored in PostgreSQL

Parameters:

- q : search param
- p : page number
- ps : page size
- l : language used to parse the query
