# Copyright 2025 Laurent Defert
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

import json
import logging
import re

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import format_html

from sosse.conf import DEFAULT_USER_AGENT

from .browser_request import requests_params
from .utils import build_multiline_re, validate_multiline_re

webhooks_logger = logging.getLogger("webhooks")


def parse_headers(headers):
    _headers = {}
    for line_no, header in enumerate(headers.split("\n")):
        if not header:
            continue
        if ":" not in header:
            raise ValueError(f"Invalid header, line {line_no + 1}: {header}")
        key, value = header.split(":", 1)
        _headers[key.strip()] = value.strip()
    return _headers


def validate_template(value):
    from .document import Document

    doc = Document(title="Test title", content="Test content")
    try:
        Webhook._render_template(doc, value)
    except ValueError as e:
        raise ValidationError(str(e))


def webhook_html_status(result):
    status_code = result.get("status_code")
    icon = "icon-no.svg"
    if isinstance(status_code, int) and 200 <= status_code < 300:
        icon = "icon-yes.svg"
    if result.get("status_code") is None or result.get("status_string") is None:
        status = "Error"
    else:
        status = f"{result.get('status_code')} {result.get('status_string')}"
    message = result.get("error") or result.get("response") or ""
    return format_html(
        '<pre style="margin-top: 0; overflow-x: auto"><img src="{}" /> {}\n{}</pre>',
        f"{settings.STATIC_URL}admin/img/{icon}",
        status,
        message,
    )


class Webhook(models.Model):
    HTTP_METHODS = (
        ("get", "GET"),
        ("post", "POST"),
        ("put", "PUT"),
        ("patch", "PATCH"),
        ("delete", "DELETE"),
    )

    TRIGGER_COND_DISCOVERY = "discovery"
    TRIGGER_COND_ON_CHANGE = "change"
    TRIGGER_COND_ALWAYS = "always"
    TRIGGER_COND_MANUAL = "manual"
    TIGGER_CONDITION = [
        (TRIGGER_COND_ON_CHANGE, "On content change"),
        (TRIGGER_COND_DISCOVERY, "On discovery"),
        (TRIGGER_COND_ALWAYS, "On every crawl"),
        (TRIGGER_COND_MANUAL, "On content change or manual crawl"),
    ]

    name = models.CharField(max_length=512, unique=True)
    trigger_condition = models.CharField(
        default=TRIGGER_COND_MANUAL,
        max_length=10,
        choices=TIGGER_CONDITION,
    )
    url = models.URLField()
    method = models.CharField(max_length=10, choices=HTTP_METHODS, default="post")
    username = models.CharField(
        max_length=128, blank=True, help_text="Username for basic authentication, leave empty for no auth"
    )
    password = models.CharField(
        max_length=128, blank=True, help_text="Password for basic authentication, leave empty for no auth"
    )
    headers = models.TextField(
        blank=True, help_text="Additional headers to send with the request", validators=[parse_headers]
    )
    body_template = models.TextField(
        blank=True, help_text="Template for the request body", validators=[validate_template], default=dict
    )
    mimetype_re = models.CharField(
        blank=True,
        default=".*",
        help_text="Run the webhook on pages with mimetype matching this regex",
        max_length=128,
        verbose_name="Mimetype regex",
        validators=[validate_multiline_re],
    )
    title_re = models.TextField(
        blank=True,
        default=".*",
        help_text="Run the webhook on pages with title matching these regexs. (one by line, lines starting with # are ignored)",
        verbose_name="Title regex",
        validators=[validate_multiline_re],
    )
    content_re = models.TextField(
        help_text="Run the webhook on pages with content matching this regexs. (one by line, lines starting with # are ignored)",
        blank=True,
        default=".*",
        verbose_name="Content regex",
        validators=[validate_multiline_re],
    )

    class Meta:
        verbose_name = "📡 Webhook"
        verbose_name_plural = "📡 Webhooks"

    def __str__(self):
        return f"Webook {self.name}"

    @classmethod
    def trigger(cls, webhooks, doc):
        # During crawling `doc` is not yet saved, its content is not yet in the database
        # so we have to check if the webhook should be triggered on the current document
        # so we iterate on all webhooks (instead of filtering them with the regexp, PG side)
        for webhook in webhooks:
            mimetype_re = build_multiline_re(webhook.mimetype_re)
            if not re.match(mimetype_re, doc.mimetype):
                continue

            title_re = build_multiline_re(webhook.title_re)
            if not re.match(title_re, doc.title):
                continue

            content_re = build_multiline_re(webhook.content_re)
            if not re.match(content_re, doc.content):
                continue

            result = webhook.send(doc)
            doc.webhooks_result[webhook.id] = result

            status_code = result.get("status_code") or 0
            if result.get("error") or status_code < 200 or status_code >= 400:
                doc.error = f"Webhook {webhook.name} failed"

    @classmethod
    def _render_fields(cls, doc_data, body_data):
        # Iterate over the fields of the serializer and replace the placeholders in the template
        def replace_var(match):
            var_name = match.group(1)
            if var_name not in doc_data:
                raise ValueError(f"Field {var_name} does not exist in document")
            return str(doc_data[var_name])

        for key, val in body_data.items():
            if isinstance(val, dict):
                body_data[key] = cls._render_fields(doc_data, val)
            elif isinstance(val, str):
                body_data[key] = re.sub(r"\$(\w+)", replace_var, val)
        return body_data

    @classmethod
    def _render_template(cls, doc, body_template):
        from .rest_api import DocumentSerializer

        try:
            body_template = json.loads(body_template)
        except ValueError as e:
            raise ValueError(f"Invalid JSON: {e}")

        serializer = DocumentSerializer(instance=doc)
        doc_data = dict(serializer.data)

        return json.dumps(cls._render_fields(doc_data, body_template))

    def send(self, doc):
        body = self._render_template(doc, self.body_template)

        params = requests_params(
            {
                "headers": {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": DEFAULT_USER_AGENT,
                }
                | parse_headers(self.headers)
            }
        )

        if self.username and self.password:
            params["auth"] = (self.username, self.password)

        method = getattr(requests, self.method)
        try:
            r = method(self.url, data=body, **params)
            if r.status_code < 200 or r.status_code >= 300:
                webhooks_logger.error(f"Webhook {self.name} failed: {r.status_code} {r.reason} {r.text}")
            return {
                "status_code": r.status_code,
                "status_string": r.reason,
                "response": r.text,
                "error": None,
            }
        except requests.exceptions.RequestException as e:
            webhooks_logger.error(f"Webhook {self.name} failed: {e}")

            return {
                "status_code": None,
                "status_string": None,
                "response": None,
                "error": str(e),
            }
