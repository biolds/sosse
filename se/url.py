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

import os
import re

from copy import copy
from urllib.parse import urlparse as base_urlparse
from urllib.parse import quote, quote_plus, unquote, unquote_plus

from django.core.exceptions import ValidationError


def norm_url_path(p):
    p = p.split('/')

    while '.' in p:
        idx = p.index('.')
        # keep last '' as it's there for the trailing /
        if idx == len(p) - 1:
            p[-1] = ''
            break

        p.remove('.')

    while '..' in p:
        idx = p.index('..')
        if idx == len(p) - 1:
            # When removing the last element, keep a trailing /
            p.append('')

        p.pop(idx)
        if idx > 0:
            p.pop(idx - 1)

    while '' in p:
        idx = p.index('')
        # keep last '' as it's there for the trailing /
        if idx == len(p) - 1:
            break

        p.remove('')

    return '/' + '/'.join(p)


def url_remove_query_string(url):
    return url.split('?', 1)[0]


def url_remove_fragment(url):
    return url.split('#', 1)[0]


def sanitize_url(_url):
    url = urlparse(_url)

    if not url.scheme:
        raise Exception(f'url has no scheme ({_url})')
    if not url.netloc and not url.path:
        raise Exception(f'url has no netloc and no path ({_url})')

    # normalize percent-encoding
    # (https://datatracker.ietf.org/doc/html/rfc3986.html#section-2.2)
    # all reserved character ^ don't require escaping, and already escaped (with % encoding)
    # characters must not be escaped a second time
    _path = quote(url.path, safe='%_.-~:/?#[]@!$&\'()*+,;=')
    url = url._replace(path=_path)

    _query = unquote_plus(url.query)
    url = url._replace(query=quote_plus(_query, safe='&='))

    # normalize punycode
    try:
        url.netloc.encode('ascii')
    except UnicodeEncodeError:
        try:
            url = url._replace(netloc=url.netloc.encode('idna').decode())
        except:  # noqa: E722
            pass

    new_path = norm_url_path(url.path)
    url = url._replace(path=new_path)
    url = url.geturl()
    return url


def urlparse(url):
    # handle malformed url with no scheme, like:
    if url.startswith('//') or url.startswith(':/'):
        url = 'fake://' + url.lstrip(':').lstrip('/')
        url = base_urlparse(url)
        return url._replace(scheme='')

    if url.startswith('http:') or url.startswith('https:'):
        scheme, url = url.split(':', 1)
        url = scheme + '://' + url.lstrip('/')

    parsed = base_urlparse(url)
    if parsed.netloc and parsed.path == '':
        parsed = parsed._replace(path='/')
    return parsed


def absolutize_url(url, link):
    if link.startswith('data:'):
        return link

    # see https://datatracker.ietf.org/doc/html/rfc3986
    _url = urlparse(url)
    _link = urlparse(link)

    if _link.scheme and not has_browsable_scheme(link):
        return link

    target = copy(_url)

    if _link.scheme:
        target = _link
    elif _link.netloc:
        target = _link._replace(scheme=_url.scheme)
    elif _link.path:
        if _link.path.startswith('/'):
            target_path = _link.path
        else:
            target_path = _link.path
            new_path = os.path.dirname(_url.path)
            if not new_path.endswith('/'):
                new_path += '/'
            target_path = new_path + _link.path

        target = target._replace(path=target_path,
                                 query=_link.query,
                                 fragment=_link.fragment,
                                 params=_link.params)
    else:
        _path = _url.path
        params = _url.params
        query = _url.query
        fragment = _url.fragment
        if _link.params:
            _path = os.path.dirname(_path) + '/'
            params = _link.params

        if _link.params or _link.query:
            query = _link.query

        if _link.params or _link.query or _link.fragment:
            fragment = _link.fragment

        target = target._replace(path=_path,
                                 params=params,
                                 query=query,
                                 fragment=fragment)
    return sanitize_url(target.geturl())


def validate_url(url):
    URL_REGEXP = r'https?://[a-zA-Z0-9_-][a-zA-Z0-9\_\-\.]*(:[0-9]+)?/[a-zA-Z0-9\%\_\.\-\~\/\?\#\[\]\@\!\$\&\'\(\)\*\+\,\;\=]*$'
    if not re.match(URL_REGEXP, url):
        raise ValidationError('URL must match the regular expression: %s' % URL_REGEXP)


# https://datatracker.ietf.org/doc/html/rfc3986#section-3.1
SCHEME_RE = '[a-zA-Z][a-zA-Z0-9+.]*:'


def has_browsable_scheme(url):
    try:
        urlparse(url)
    except ValueError:
        return False

    if url.startswith('#'):
        return False

    if re.match(SCHEME_RE, url):
        scheme = url.split(':', 1)[0]
        return scheme in ('http', 'https')

    return True


def url_beautify(url):
    url = urlparse(url)
    _netloc = url.netloc.encode().decode('idna')
    _path = unquote(url.path)
    _query = unquote_plus(url.query)
    url = url._replace(netloc=_netloc, path=_path, query=_query)
    return url.geturl()
