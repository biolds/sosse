# Copyright 2022-2023 Laurent Defert
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

from collections import OrderedDict
from configparser import ConfigParser

from django.core.management.utils import get_random_secret_key


CONF_FILE = '/etc/sosse/sosse.conf'


DEFAULTS = OrderedDict([
    ['common', OrderedDict([
        ['secret_key', {
            'var': 'SECRET_KEY',
            'comment': 'SECURITY WARNING: keep the secret key used in production secret!\nRun "sosse-admin generate_secret" to create a new one\nSee https://docs.djangoproject.com/en/3.2/ref/settings/#secret-key',
            'default': 'CHANGE ME'
        }],
        ['debug', {
            'var': 'DEBUG',
            'comment': "SECURITY WARNING: don't run with debug turned on in production!",
            'type': bool,
            'default': False
        }],
        ['db_name', {
            'comment': 'Postgresql connection parameters',
            'default': 'sosse'
        }],
        ['db_user', {
            'default': 'sosse'
        }],
        ['db_pass', {
            'default': 'CHANGE ME'
        }],
        ['db_host', {
            'default': '127.0.0.1'
        }],
        ['db_port', {
            'default': 5432,
            'type': int
        }]
    ])],
    ['webserver', OrderedDict([
        ['anonymous_search', {
            'comment': 'Anonymous users (users not logged in) can do searches',
            'default': False,
            'type': bool
        }],
        ['rss_access_token', {
            'comment': 'When anonymous search are disabled a token can be used to access RSS feeds without authenticating\nThe token can be passed to HTTP reqeuests as an url parameter, for example "?token=<RSS access token>"\nSetting an empty string disables token access',
            'default': '',
            'type': str
        }],
        ['search_shortcut', {
            'comment': 'Special character used as search shortcut',
            'default': '!',
            'type': str
        }],
        ['allowed_host', {
            'comment': 'FDQN of the webserver, "*" for any, see https://docs.djangoproject.com/en/3.2/ref/settings/#allowed-hosts',
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
            'comment': 'https://docs.djangoproject.com/en/3.2/ref/settings/#use-tz',
            'default': True,
            'type': bool
        }],
        ['timezone', {
            'var': 'TIME_ZONE',
            'comment': 'See https://docs.djangoproject.com/en/3.2/ref/settings/#time-zone',
            'default': 'UTC'
        }],
        ['default_page_size', {
            'comment': 'Default result count returned',
            'default': 20,
            'type': int
        }],
        ['max_page_size', {
            'comment': 'Maximum user-defined result count',
            'default': 200,
            'type': int
        }],
        ['data_upload_max_memory_size', {
            'comment': 'https://docs.djangoproject.com/en/4.1/ref/settings/#data-upload-max-memory-size',
            'default': 2621440,
            'type': int
        }],
        ['data_upload_max_number_fields', {
            'comment': 'https://docs.djangoproject.com/en/4.1/ref/settings/#data-upload-max-number-fields',
            'default': 1000,
            'type': int
        }],
        ['atom_feed_size', {
            'comment': 'Size of Atom feeds',
            'default': 200,
            'type': int
        }],
        ['exclude_not_indexed', {
            'comment': 'Exclude page queued for indexing, but not yet indexed from search results',
            'default': True,
            'type': bool
        }],
        ['exclude_redirect', {
            'comment': 'Exclude page redirection from search results',
            'default': True,
            'type': bool
        }],
        ['crawl_status_autorefresh', {
            'comment': 'Delay between crawl status page autorefresh (in seconds)',
            'default': 5,
            'type': int
        }],
    ])],
    ['crawler', OrderedDict([
        ['crawler_count', {
            'comment': 'Number of crawlers running concurrently (default to the number of CPU available)',
            'default': ''
        }],
        ['proxy', {
            'comment': 'Url of the HTTP proxy server to use',
            'default': ''
        }],
        ['user_agent', {
            'comment': 'User agent used by crawlers',
            'default': 'SOSSE'
        }],
        ['fail_over_lang', {
            'comment': 'Language used to parse web pages when the original language could not be detected',
            'default': 'english'
        }],
        ['hashing_algo', {
            'comment': 'Hashing algorithms used to define if the content of a pae has changed',
            'default': 'md5'
        }],
        ['screenshots_size', {
            'comment': 'Resolution of the browser used to take screenshots',
            'default': '1920x1080'
        }],
        ['browser_options', {
            'comment': "Options passed to Chromium's command line",
            'default': '--enable-precise-memory-info --disable-default-apps --incognito --headless'
        }],
        ['js_stable_time', {
            'comment': 'When loading a page in a browser, it is processed after the page stays unchanged for <js_stable_time> seconds',
            'default': 0.1,
            'type': float
        }],
        ['js_stable_retry', {
            'comment': 'Check at most <js_stable_retry> times for the page to stay unchanged before processing',
            'default': 100,
            'type': int
        }],
        ['tmp_dl_dir', {
            'comment': 'Base directory where files are temporarily downloaded',
            'default': '/var/lib/sosse/downloads'
        }],
        ['dl_check_time', {
            'comment': 'Download detection will every <dl_check_time> seconds for a started download',
            'default': 0.1,
            'type': float
        }],
        ['dl_check_retry', {
            'comment': 'Download detection will retry <dl_check_retry> times for a started download',
            'default': 2,
            'type': int
        }],
        ['browser_crash_sleep', {
            'comment': 'Sleep <browser_crash_sleep> seconsds before retrying after the browser crashed',
            'default': 1.0,
            'type': float
        }],
        ['browser_crash_retry', {
            'comment': 'Retry <browser_crash_retry> time to index the page on browser crashes',
            'default': 1,
            'type': int
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
    },
}


class Conf:
    @classmethod
    def get(cls):
        settings = {}

        # Set defaults
        for section, conf in DEFAULTS.items():
            for key, val in conf.items():
                var_name = val.get('var', 'SOSSE_' + key.upper())
                settings[var_name] = val['default']

        # Read the real conf
        conf = ConfigParser()
        conf.read(CONF_FILE)
        for section in conf.sections():
            if section not in DEFAULTS:
                raise Exception('Invalid section "%s"' % section)

            for key, value in conf[section].items():
                if key not in DEFAULTS[section]:
                    raise Exception('Invalid option "%s" found in section %s' % (key, section))

                var_name = DEFAULTS[section][key].get('var', 'SOSSE_' + key.upper())
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

        crawler_count = settings.pop('SOSSE_CRAWLER_COUNT')
        if not crawler_count:
            crawler_count = None
        else:
            try:
                crawler_count = int(crawler_count)
            except ValueError:
                raise Exception('Configuration parsing error: invalid "crawler_count", must be an integer or empty: %s' % crawler_count)

        if settings['DEBUG']:
            LOGGING['loggers']['crawler']['level'] = 'DEBUG'
            LOGGING['loggers']['web']['level'] = 'DEBUG'

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
                comment = '\n'.join('# ' + line.strip() for line in comment.splitlines())
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
