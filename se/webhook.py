# Copyright 2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
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

from .browser import SkipIndexing
from .browser_request import requests_params
from .tag import Tag
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
        Webhook._render_template(doc, value, validator=True)
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


def dotted_json_path_validator(value):
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", value):
        raise ValidationError(
            "Invalid dotted JSON path. It should start with a letter or underscore and contain only letters, "
            "digits, and underscores."
        )
    return value


def get_subobject(obj, path):
    if not path:
        return obj
    keys = path.split(".")
    for key in keys:
        if isinstance(obj, dict) and key in obj:
            obj = obj[key]
        elif isinstance(obj, list) and key.isdigit() and int(key) < len(obj):
            obj = obj[int(key)]
        else:
            raise ValueError(f"Invalid path: {path}")
    return obj


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
    enabled = models.BooleanField(default=True)
    trigger_condition = models.CharField(
        default=TRIGGER_COND_MANUAL,
        max_length=10,
        choices=TIGGER_CONDITION,
    )
    updates_doc = models.BooleanField(default=False, verbose_name="Overwrite document's fields with webhook response")
    update_json_path = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="Path in JSON response",
        help_text="The dotted path in the JSON response to the value used for updating the document. If left empty, "
        "the entire response will be used to update the document.",
        validators=[dotted_json_path_validator],
    )
    update_json_deserialize = models.BooleanField(
        default=False,
        verbose_name="Deserialize the response before updating the document",
        help_text="If checked, the response will be deserialized as JSON before updating the document.",
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
        help_text="Template for the request body",
        validators=[validate_template],
        default=dict,
        verbose_name="JSON body template",
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        help_text="Run the webhook on documents with all these tags, their children, or all if none are specified",
        verbose_name="Tags",
    )
    url_re = models.TextField(
        blank=True,
        default=".*",
        help_text="Run the webhook on pages with URL matching this regex (one per line; lines starting with # are ignored)",
        verbose_name="URL regex",
        validators=[validate_multiline_re],
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

    def __str__(self):
        return f"Webook {self.name}"

    def get_title_label(self):
        return self.name

    @classmethod
    def trigger(cls, webhooks, doc):
        from .rest_api import DocumentSerializer

        # During crawling `doc` is not yet saved, its content is not yet in the database
        # so we have to check if the webhook should be triggered on the current document
        # so we iterate on all webhooks (instead of filtering them with the regexp, PG side)
        for webhook in webhooks.filter(enabled=True).order_by("name"):
            if webhook.tags.exists():
                has_all_tags = True
                doc_tags = set()

                for tag in doc.tags.all():
                    doc_tags |= set(tag.get_tree())

                for tag in webhook.tags.all():
                    if tag not in doc_tags:
                        has_all_tags = False
                        break
                if not has_all_tags:
                    continue

            url_re = build_multiline_re(webhook.url_re)
            if not re.match(url_re, doc.url):
                continue
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
            elif webhook.updates_doc:
                response = result.get("response")
                try:
                    body = json.loads(response)
                except json.JSONDecodeError as e:
                    raise SkipIndexing(
                        f"Webhook {webhook.name} failed to decode response:\n{e}\nInput data was:\n{response}\n---"
                    )

                body = get_subobject(body, webhook.update_json_path) if webhook.update_json_path else body

                if webhook.update_json_deserialize:
                    try:
                        body = json.loads(body)
                    except json.JSONDecodeError as e:
                        raise SkipIndexing(
                            f"Webhook {webhook.name} failed to deserialize response:\n{e}\nInput data was:\n{body}\n---"
                        )
                serializer = DocumentSerializer(doc, data=body, partial=True)
                serializer.user_doc_update("Webhook")

    @classmethod
    def _replace_placeholders(cls, doc_data, value, validator):
        def replace_var(match):
            var_name = match.group(1)
            _doc_data = get_subobject(doc_data, var_name)
            return str(_doc_data)

        try:
            return re.sub(r"\$\{([\w.]+)\}", replace_var, value)
        except ValueError:
            if validator:
                return {}
            raise

    @classmethod
    def _render_fields(cls, doc_data, body_data, validator):
        for key, val in body_data.items():
            if isinstance(val, dict):
                body_data[key] = cls._render_fields(doc_data, val, validator)
            elif isinstance(val, list):
                body_data[key] = [
                    cls._replace_placeholders(doc_data, item, validator)
                    if isinstance(item, str)
                    else cls._render_fields(doc_data, item, validator)
                    for item in val
                ]
            elif isinstance(val, str):
                body_data[key] = cls._replace_placeholders(doc_data, val, validator)
        return body_data

    @classmethod
    def _render_template(cls, doc, body_template, validator=False):
        from .rest_api import DocumentSerializer

        try:
            body_template = json.loads(body_template, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid JSON: {e}")

        serializer = DocumentSerializer(instance=doc)
        doc_data = dict(serializer.data)

        return json.dumps(cls._render_fields(doc_data, body_template, validator=validator))

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
