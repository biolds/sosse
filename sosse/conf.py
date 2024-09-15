# Copyright 2022-2024 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

import hashlib
import os
import sys

from collections import OrderedDict
from configparser import ConfigParser

from django.core.management.utils import get_random_secret_key


CONF_FILE = '/etc/sosse/sosse.conf'


DEFAULTS = OrderedDict([
    ['common', OrderedDict([
        ['secret_key', {
            'var': 'SECRET_KEY',
            'comment': 'Run ``sosse-admin generate_secret`` to create a new one.\nSee https://docs.djangoproject.com/en/3.2/ref/settings/#secret-key\n\n.. warning::\n   Keep the secret key used in production secret!',
            'default': 'CHANGE ME'
        }],
        ['debug', {
            'var': 'DEBUG',
            'comment': "Debug mode.\n\n.. warning::\n   Don't run with debug turned on in production!",
            'type': bool,
            'default': False
        }],
        ['db_name', {
            'comment': 'PostgreSQL connection parameters.',
            'doc': 'PostgreSQL database name.',
            'default': 'sosse'
        }],
        ['db_user', {
            'default': 'sosse',
            'doc': 'PostgreSQL username.',
        }],
        ['db_pass', {
            'default': 'CHANGE ME',
            'doc': 'PostgreSQL password.',
        }],
        ['db_host', {
            'default': '127.0.0.1',
            'doc': 'PostgreSQL hostname or IP address.',
        }],
        ['db_port', {
            'default': 5432,
            'type': int,
            'doc': 'PostgreSQL port.',
        }]
    ])],
    ['webserver', OrderedDict([
        ['anonymous_search', {
            'comment': 'Anonymous users (users not logged in) can do searches.',
            'default': False,
            'type': bool
        }],
        ['atom_access_token', {
            'comment': 'When anonymous search are disabled a token can be used to access Atom feeds without authenticating.\nThe token can be passed to HTTP requests as an url parameter, for example ``?token=<Atom access token>``.\nSetting an empty string disables token access.',
            'default': '',
        }],
        ['search_shortcut_char', {
            'comment': 'Special character used as search shortcut.',
            'default': '!',
        }],
        ['default_search_redirect', {
            'comment': 'Default search engine to use.\nLeave empty to use SOSSE by default, use the search engine "Short name" otherwise\n\n.. warning::\n   This field is case sensitive.',
            'default': '',
        }],
        ['online_search_redirect', {
            'comment': 'Search engine to use when the connectivity check succeeds (see `online_check_url`).\nLeave empty to use the `default_search_redirect` by default, use the search engine "Short name" otherwise\n\n.. warning::\n   This field is case sensitive.',
            'default': '',
        }],
        ['online_check_url', {
            'comment': 'URL used to define online or offline mode.',
            'default': 'https://google.com/',
        }],
        ['online_check_timeout', {
            'comment': 'Timeout in seconds used to define online or offline mode.',
            'default': 1.0,
            'type': float,
        }],
        ['online_check_cache', {
            'comment': 'Online check is done once every ``online_check_cache`` request. The special value ``once`` can be used to run the check only once, when the first request is done. ``0`` can be used to disable caching.\n\n.. note::\n   The cache is effective on a uwSGI worker basis, and as long as the uWSGI worker is alive. So even with a value of ``once`` a new request will be done everytime a new worker is spawned.',
            'default': '10',
        }],
        ['sosse_shortcut', {
            'comment': 'In case the default_shortcut is not empty this defines which shortcut searches SOSSE.',
            'default': '',
        }],
        ['allowed_host', {
            'comment': 'FDQN of the webserver, "*" for any.\nSee https://docs.djangoproject.com/en/3.2/ref/settings/#allowed-hosts',
            'default': '*'
        }],
        ['static_url', {
            'var': 'STATIC_URL',
            'default': '/static/'
        }],
        ['static_root', {
            'var': 'STATIC_ROOT',
            'default': '/var/lib/sosse/static/'
        }],
        ['screenshots_url', {
            'default': '/screenshots/'
        }],
        ['screenshots_dir', {
            'default': '/var/lib/sosse/screenshots/'
        }],
        ['html_snapshot_url', {
            'comment': 'Url path to HTML snapshot\n\n.. danger::\n   This value is hardcoded inside stored HTML snapshot. If you modify it, any HTML page previously stored as a snapshot will need to be crawled again in order to update internal links.',
            'default': '/snap/'
        }],
        ['html_snapshot_dir', {
            'default': '/var/lib/sosse/html/'
        }],
        ['use_i18n', {
            'var': 'USE_I18N',
            'comment': 'See https://docs.djangoproject.com/en/3.2/ref/settings/#use-i18n',
            'default': True,
            'type': bool
        }],
        ['use_l10n', {
            'var': 'USE_L10N',
            'comment': 'See https://docs.djangoproject.com/en/3.2/ref/settings/#use-l10n',
            'default': True,
            'type': bool
        }],
        ['language_code', {
            'var': 'LANGUAGE_CODE',
            'comment': 'See https://docs.djangoproject.com/en/3.2/ref/settings/#language-code',
            'default': 'en-us'
        }],
        ['datetime_format', {
            'var': 'DATETIME_FORMAT',
            'comment': 'See https://docs.djangoproject.com/en/3.2/ref/settings/#datetime-format',
            'default': 'N j, Y, P'
        }],
        ['use_tz', {
            'var': 'USE_TZ',
            'comment': 'See https://docs.djangoproject.com/en/3.2/ref/settings/#use-tz',
            'default': True,
            'type': bool
        }],
        ['timezone', {
            'var': 'TIME_ZONE',
            'comment': 'See https://docs.djangoproject.com/en/3.2/ref/settings/#time-zone',
            'default': 'UTC'
        }],
        ['default_page_size', {
            'comment': 'Default result count returned.',
            'default': 20,
            'type': int
        }],
        ['max_page_size', {
            'comment': 'Maximum user-defined result count.',
            'default': 200,
            'type': int
        }],
        ['data_upload_max_memory_size', {
            'comment': 'See https://docs.djangoproject.com/en/3.2/ref/settings/#data-upload-max-memory-size',
            'default': 2621440,
            'type': int
        }],
        ['data_upload_max_number_fields', {
            'comment': 'See https://docs.djangoproject.com/en/3.2/ref/settings/#data-upload-max-number-fields',
            'default': 1000,
            'type': int
        }],
        ['atom_feed_size', {
            'comment': 'Number of result returned by Atom feeds.',
            'default': 200,
            'type': int
        }],
        ['exclude_not_indexed', {
            'comment': 'Exclude page queued for indexing but not yet indexed from search results.',
            'default': True,
            'type': bool
        }],
        ['exclude_redirect', {
            'comment': 'Exclude page redirection from search results.',
            'default': True,
            'type': bool
        }],
        ['cache_follows_redirect', {
            'comment': 'Accessing a cached page of a redirection url automatically follows the redirection.',
            'default': True,
            'type': bool
        }],
        ['admin_page_size', {
            'comment': 'Number of items by list in the administration pages.',
            'default': 100,
            'type': int
        }],
        ['search_strip', {
            'comment': 'Removes this string from search queries.',
            'default': '',
        }],
        ['crawl_status_autorefresh', {
            'comment': 'Delay between crawl status page autorefresh (in seconds).',
            'default': 5,
            'type': int
        }],
        ['browsable_home', {
            'comment': 'Display entry point documents on the homepage.',
            'default': True,
            'type': bool
        }],
        ['links_no_referrer', {
            'comment': 'Omit the `referrer header <https://en.wikipedia.org/wiki/HTTP_referrer>`_ when accessing external links.',
            'default': True,
            'type': bool
        }],
        ['links_new_tab', {
            'comment': 'Open external links in a new tab.',
            'default': False,
            'type': bool
        }]
    ])],
    ['crawler', OrderedDict([
        ['crawler_count', {
            'comment': 'Number of crawlers running concurrently (defaults to the number of CPU available).',
            'default': ''
        }],
        ['proxy', {
            'comment': 'Url of the HTTP proxy server to use.\nExample: http://192.168.0.1:8080/',
            'default': ''
        }],
        ['user_agent', {
            'comment': 'User agent sent by crawlers.',
            'default': 'SOSSE'
        }],
        ['requests_timeout', {
            'comment': 'Timeout in secounds when retrieving pages with Requests (no timeout if 0).',
            'default': 10,
            'type': int
        }],
        ['fail_over_lang', {
            'comment': 'Language used to parse web pages when the original language could not be detected.',
            'default': 'english'
        }],
        ['hashing_algo', {
            'comment': 'Hashing algorithms used to define if the content of a page has changed.',
            'default': 'md5'
        }],
        ['screenshots_size', {
            'comment': 'Resolution of the browser used to take screenshots.',
            'default': '1920x1080'
        }],
        ['default_browser', {
            'comment': 'Defines which browser to use by default when browsing mode is auto-detected (can be either "firefox" or "chromium").',
            'default': 'chromium'
        }],
        ['chromium_options', {
            'comment': "Options passed to Chromium's command line.\nYou may need to add ``--no-sandbox`` to run the crawler as root,\nor ``--disable-dev-shm-usage`` to run in a virtualized container.",
            'default': '--enable-precise-memory-info --disable-default-apps --headless'
        }],
        ['firefox_options', {
            'comment': "Options passed to Firefox's command line.",
            'default': '--headless'
        }],
        ['js_stable_time', {
            'comment': 'When loading a page in a browser, wait ``js_stable_time`` seconds before checking the DOM stays unchanged.',
            'default': 0.1,
            'type': float
        }],
        ['js_stable_retry', {
            'comment': 'Check at most ``js_stable_retry`` times for the page to stay unchanged before processing.',
            'default': 100,
            'type': int
        }],
        ['tmp_dl_dir', {
            'comment': 'Base directory where files are temporarily downloaded.',
            'default': '/var/lib/sosse/downloads'
        }],
        ['browser_config_dir', {
            'comment': 'Base directory where browser configuration files and profiles are stored.',
            'default': '/var/lib/sosse/browser_config'
        }],
        ['dl_check_time', {
            'comment': 'Download detection will every ``dl_check_time`` seconds for a started download.',
            'default': 0.1,
            'type': float
        }],
        ['dl_check_retry', {
            'comment': 'Download detection will retry ``dl_check_retry`` times for a started download.',
            'default': 2,
            'type': int
        }],
        ['max_file_size', {
            'comment': 'Maximum file size to index (in kB).',
            'default': 500,
            'type': int
        }],
        ['max_html_asset_size', {
            'comment': 'Maximum file size of html assets (css, images, etc.) to download (in kB).',
            'default': 5000,
            'type': int
        }],
        ['max_redirects', {
            'comment': 'Maximum numbers of redirect before aborting.\n(this is accurate when using Requests only,\nsome redirects may be missed on Chromium)',
            'default': 5,
            'type': int
        }],
        ['browser_idle_exit_time', {
            'comment': 'Close the browser when the crawler is idle for ``browser_idle_exit_time`` seconds.',
            'default': 5,
            'type': int
        }],
        ['browser_crash_sleep', {
            'comment': 'Sleep ``browser_crash_sleep`` seconds before retrying after the browser crashed.',
            'default': 1.0,
            'type': float
        }],
        ['browser_crash_retry', {
            'comment': 'Retry ``browser_crash_retry`` times to index the page on browser crashes.',
            'default': 1,
            'type': int
        }],
        ['css_parser', {
            'comment': 'Choose which CSS parser implementation to use. May be one of ``internal`` or ``cssutils``:\nYou may want to change this option when HTML snapshots have broken styles.',
            'default': 'internal',
        }],
    ])]
])


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'timestamp': {
            'format': '{asctime} {process} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'crawler_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/sosse/crawler.log',
            'formatter': 'timestamp'
        },
        'webserver_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/sosse/webserver.log',
            'formatter': 'timestamp'
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['webserver_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'web': {
            'handlers': ['webserver_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'crawler': {
            'handlers': ['crawler_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'html_snapshot': {
            'handlers': ['crawler_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


class Conf:
    @classmethod
    def get(cls):
        settings = {}

        # Read the real conf
        conf = ConfigParser()
        try:
            conf.read_file(open(CONF_FILE), CONF_FILE)
        except FileNotFoundError:
            if 'default_conf' in sys.argv:
                print('WARNING: Configuration file %s is missing' % CONF_FILE, file=sys.stderr)

        for section in conf.sections():
            if section not in DEFAULTS:
                raise Exception('Invalid section "%s"' % section)

            for key, value in conf[section].items():
                if key not in DEFAULTS[section]:
                    raise Exception('Invalid option "%s" found in section %s' % (key, section))

        for section, default_conf in DEFAULTS.items():
            for key, val in default_conf.items():
                # Set defaults
                var_name = val.get('var', 'SOSSE_' + key.upper())
                settings[var_name] = val['default']

                default_var_name = 'SOSSE_' + key.upper()
                if default_var_name in os.environ:
                    value = os.environ[default_var_name]
                elif section in conf.sections() and key in conf[section]:
                    value = conf[section][key]
                else:
                    continue

                var_name = DEFAULTS[section][key].get('var', default_var_name)
                var_type = DEFAULTS[section][key].get('type', str)

                if var_type == bool:
                    settings[var_name] = value.lower() not in ('false', 'no', '')
                elif var_type in (int, float):
                    try:
                        settings[var_name] = var_type(value)
                    except ValueError:
                        t = {
                            int: 'integer',
                            float: 'float number'
                        }[var_type]
                        raise Exception('Configuration parsing error: in section "%s", "%s" option is not a valid %s: %s' % (section, key, t, value))
                else:
                    settings[var_name] = value

        hash_algo = settings.pop('SOSSE_HASHING_ALGO')
        algos = []
        for a in dir(hashlib):
            try:
                b = getattr(hashlib, a)
                fake_hash = b(b'')
                if hasattr(fake_hash, 'hexdigest'):
                    algos.append(a)
            except TypeError:
                pass
        if hash_algo not in algos:
            raise Exception('Configuration parsing error: invalid hashing_algo value "%s", must be one of %s' % (hash_algo, ', '.join(sorted(algos))))

        css_parser = settings.get('SOSSE_CSS_PARSER')
        if css_parser not in ('internal', 'cssutils'):
            raise Exception('Configuration parsing error: invalid css_parser value "%s", it must be either "internal" or "cssutils"')

        crawler_count = settings.pop('SOSSE_CRAWLER_COUNT')
        if not crawler_count:
            crawler_count = None
        else:
            try:
                crawler_count = int(crawler_count)
            except ValueError:
                raise Exception('Configuration parsing error: invalid "crawler_count", must be an integer or empty: %s' % crawler_count)

        if settings.get('SOSSE_DEFAULT_SEARCH_REDIRECT') and settings.get('SOSSE_ONLINE_SEARCH_REDIRECT'):
            raise Exception('Options "default_search_redirect" and "online_search_redirect" cannot be set at the same time.')

        if not settings.get('SOSSE_ONLINE_CHECK_URL') and settings.get('SOSSE_ONLINE_SEARCH_REDIRECT'):
            raise Exception('Options "online_check_url" is required when "online_search_redirect" is set.')

        online_check_cache = settings.get('SOSSE_ONLINE_CHECK_CACHE')
        if online_check_cache == 'once':
            online_check_cache = None
        else:
            try:
                online_check_cache = int(online_check_cache)
            except ValueError:
                raise Exception('Configuration parsing error: invalid "online_check_cache", must be an integer or "once": %s' % crawler_count)

        settings['SOSSE_ONLINE_CHECK_CACHE'] = online_check_cache

        if settings.get('SOSSE_DEFAULT_BROWSER', 'firefox') not in ('firefox', 'chromium'):
            raise Exception('Configuration parsing error: invalid default_browser, must be one of "firefox" or "chromium"')

        if settings['DEBUG']:
            for key, logger in LOGGING['loggers'].items():
                if key == 'django':
                    # skip SQL debug statement
                    continue
                logger['level'] = 'DEBUG'

        settings.update({
            'HASHING_ALGO': getattr(hashlib, hash_algo),
            'DATABASES': {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': settings.pop('SOSSE_DB_NAME'),
                    'USER': settings.pop('SOSSE_DB_USER'),
                    'PASSWORD': settings.pop('SOSSE_DB_PASS'),
                    'HOST': settings.pop('SOSSE_DB_HOST'),
                    'PORT': str(settings.pop('SOSSE_DB_PORT'))
                }
            },
            'ALLOWED_HOSTS': [settings.pop('SOSSE_ALLOWED_HOST')],
            'DATA_UPLOAD_MAX_MEMORY_SIZE': settings.pop('SOSSE_DATA_UPLOAD_MAX_MEMORY_SIZE'),
            'DATA_UPLOAD_MAX_NUMBER_FIELDS': settings.pop('SOSSE_DATA_UPLOAD_MAX_NUMBER_FIELDS'),
            'SOSSE_CRAWLER_COUNT': crawler_count,
            'LOGGING': LOGGING
        })

        for opt in ('static_url', 'static_root', 'screenshots_url', 'screenshots_dir',
                    'html_snapshot_url', 'html_snapshot_dir'):
            val = settings.get('SOSSE_' + opt.upper(), '')
            if not val.endswith('/'):
                settings['SOSSE_' + opt.upper()] = val + '/'

        settings['SOSSE_THUMBNAILS_DIR'] = settings['SOSSE_SCREENSHOTS_DIR'] + 'thumb/'
        settings['SOSSE_THUMBNAILS_URL'] = settings['SOSSE_SCREENSHOTS_URL'] + 'thumb/'
        return settings

    @classmethod
    def generate_default(cls):
        s = ''
        for section_no, (section, variables) in enumerate(DEFAULTS.items()):
            if section_no:
                s += '\n'
            s += f'[{section}]\n'

            for var_no, (var, opt) in enumerate(variables.items()):
                comment = opt.get('comment')
                if not comment:
                    comment = ''
                else:
                    comment += '\n'
                comment += 'Default: %s' % opt['default']
                comment = '\n'.join('# ' + line for line in comment.splitlines() if line)
                if var_no != 0:
                    s += '\n'
                s += f'{comment}\n'

                value = str(opt['default'])
                if opt.get('type', str) != str:
                    value = value.lower()
                s += f'#{var}={value}\n'

                if var == 'secret_key':
                    # Escape % to avoid value interpolation in the conf file
                    # (https://docs.python.org/3/library/configparser.html#interpolation-of-values)
                    s += 'secret_key = ' + get_random_secret_key().replace('%', '%%') + '\n'
        return s
