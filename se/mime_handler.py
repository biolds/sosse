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
import os
import re
import subprocess  # nosec B404
import tempfile
from mimetypes import guess_extension

from django.conf import settings
from django.db import models

from .utils import build_multiline_re, validate_multiline_re

crawl_logger = logging.getLogger("crawl_logger")


class MimeHandler(models.Model):
    IO_FORMAT_CHOICES = [
        ("json_doc", "JSON Document"),
        ("content", "Content"),
    ]

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    script = models.TextField(help_text="Shell script which receives a file path as first argument")
    mimetype_re = models.TextField(
        help_text="One regex per line to match MIME types (e.g. ^application/pdf$)",
        validators=[validate_multiline_re],
    )
    timeout = models.PositiveIntegerField(default=30, help_text="Timeout in seconds for the script execution")
    enabled = models.BooleanField(default=True)
    io_format = models.CharField(max_length=20, choices=IO_FORMAT_CHOICES, default="content")

    def get_script_path(self):
        """Returns the absolute path to the stored script file, based on PK."""
        scripts_dir = settings.SOSSE_SCRIPTS_DIR
        os.makedirs(scripts_dir, exist_ok=True)
        return os.path.join(scripts_dir, f"handler_{self.pk}.sh")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        script_path = self.get_script_path()
        try:
            with open(script_path, "w") as f:
                script = self.script.replace("\r\n", "\n")
                f.write(script)
            os.chmod(script_path, 0o700)
            crawl_logger.debug(f"Script for handler '{self.name}' saved to {script_path}")
        except Exception as e:
            crawl_logger.error(f"Error saving script for handler '{self.name}': {e}")
            raise

    def delete(self, *args, **kwargs):
        script_path = self.get_script_path()
        if os.path.exists(script_path):
            try:
                os.remove(script_path)
                crawl_logger.debug(f"Deleted script file: {script_path}")
            except Exception as e:
                crawl_logger.error(f"Failed to delete script file {script_path}: {e}")
        return super().delete(*args, **kwargs)

    def execute(self, input_file: str):
        script_path = self.get_script_path()
        args = ["/bin/bash", script_path, input_file]

        crawl_logger.debug(f"[{self.name}] Executing script: {args}")

        try:
            result = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )  # nosec B603
            crawl_logger.debug(f"[{self.name}] Return code: {result.returncode}")
            crawl_logger.debug(f"[{self.name}] STDOUT:\n{result.stdout.strip()}")
            crawl_logger.debug(f"[{self.name}] STDERR:\n{result.stderr.strip()}")
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            msg = f"[{self.name}] Timeout after {self.timeout}s"
            crawl_logger.debug(msg)
            return -1, "", msg

    @classmethod
    def run_for_document(cls, doc, page):
        from .rest_api import DocumentSerializer

        crawl_logger.debug(f"Running mime handlers for {doc.url}")

        applicable_handlers = cls.objects.filter(enabled=True).order_by("name")
        matched = False

        temp_content_path = None
        temp_json_path = None
        try:
            # Write the content from the page if necessary
            content_file = doc.get_content_file()
            if not content_file:
                extension = guess_extension(doc.mimetype)
                with tempfile.NamedTemporaryFile(mode="wb+", suffix=f".{extension}", delete=False) as temp_file:
                    temp_file.write(page.content)
                    temp_file.flush()
                    temp_content_path = temp_file.name
                    content_file = temp_content_path

            if any(h.io_format == "json_doc" for h in applicable_handlers):
                with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tf:
                    json_doc = DocumentSerializer(doc).data
                    json_doc["content_file"] = content_file
                    json.dump(json_doc, tf)
                    tf.flush()
                    temp_json_path = tf.name

            for handler in applicable_handlers:
                if re.match(build_multiline_re(handler.mimetype_re.strip()), doc.mimetype):
                    matched = True
                    crawl_logger.debug(f"[{handler.name}] Handler matched for {doc.mimetype}")

                    input_path = temp_json_path if handler.io_format == "json_doc" else content_file
                    code, stdout, stderr = handler.execute(input_path)

                    if code != 0:
                        doc.error = f"{doc.error or ''}\nExecution of {handler.name} failed with status {code}:\n{stderr}".strip()
                        continue

                    try:
                        if handler.io_format == "json_doc":
                            try:
                                data = json.loads(stdout)
                            except ValueError as e:
                                doc.error = f"{doc.error or ''}\n{handler.name} output is not valid JSON: {e}\ncontent: {stdout[:1000]}"
                                continue

                        else:
                            data = {"content": stdout}

                        if stdout:
                            serializer = DocumentSerializer(doc, data=data, partial=True)
                            serializer.is_valid(raise_exception=True)
                            serializer.update(doc, serializer.validated_data)
                    except Exception as e:
                        doc.error = f"{doc.error or ''}\n{handler.name} processing error: {e}".strip()
                        if getattr(settings, "TEST_MODE", False):
                            raise
                        continue
        finally:
            if temp_json_path and os.path.exists(temp_json_path):
                os.remove(temp_json_path)
            if temp_content_path and os.path.exists(temp_content_path):
                os.remove(temp_content_path)

        if not matched:
            crawl_logger.debug(f"No handler matched for {doc.mimetype}")

    def __str__(self):
        return self.name
