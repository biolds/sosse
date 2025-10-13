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
from PIL import Image

from .builtin import BuiltinModel
from .utils import build_multiline_re, validate_multiline_re

crawl_logger = logging.getLogger("crawler")


class MimePlugin(BuiltinModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    license = models.CharField(max_length=255, blank=True, help_text="License of the script, e.g. GPL-3.0")
    script = models.TextField(help_text="Shell script which receives a file path as first argument")
    mimetype_re = models.TextField(
        help_text="One regex per line to match MIME types (e.g. ^application/pdf$)",
        validators=[validate_multiline_re],
    )
    timeout = models.PositiveIntegerField(default=30, help_text="Timeout in seconds for the script execution")
    enabled = models.BooleanField(default=True)

    def get_script_path(self):
        """Returns the absolute path to the stored script file, based on PK."""
        scripts_dir = settings.SOSSE_SCRIPTS_DIR
        os.makedirs(scripts_dir, exist_ok=True)
        return os.path.join(scripts_dir, f"plugin_{self.pk}.sh")

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

    def execute(self, input_file: str, temp_dir: str):
        script_path = self.get_script_path()
        args = ["/bin/bash", script_path, input_file]

        crawl_logger.debug(f"[{self.name}] Executing script: {args}")

        try:
            result = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                cwd=temp_dir,
                timeout=self.timeout,
            )  # nosec B603
            crawl_logger.debug(f"[{self.name}] Return code: {result.returncode}")
            crawl_logger.debug(f"[{self.name}] STDOUT:\n{result.stdout.strip()}")
            crawl_logger.debug(f"[{self.name}] STDERR:\n{result.stderr.strip()}")
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired as e:
            stderr_msg = e.stderr.decode() if e.stderr else ""
            msg = f"{stderr_msg}\n[{self.name}] Timeout after {self.timeout}s".strip()
            crawl_logger.debug(msg)
            return -1, "", msg

    @classmethod
    def run_for_document(cls, doc, page):
        from .rest_api import DocumentSerializer

        crawl_logger.debug(f"Running mime handlers for {doc.url}")

        applicable_handlers = cls.objects.filter(enabled=True).order_by("name")
        for handler in applicable_handlers:
            if re.match(build_multiline_re(handler.mimetype_re.strip()), doc.mimetype):
                break
        else:
            crawl_logger.debug(f"No handler matched for {doc.mimetype}")
            return

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

            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tf:
                json_doc = DocumentSerializer(doc).data
                json_doc["content_file"] = content_file
                json.dump(json_doc, tf)
                tf.flush()
                temp_json_path = tf.name

            for handler in applicable_handlers:
                if re.match(build_multiline_re(handler.mimetype_re.strip()), doc.mimetype):
                    crawl_logger.debug(f"[{handler.name}] Handler matched for {doc.mimetype}")

                    with tempfile.TemporaryDirectory() as temp_dir:
                        code, stdout, stderr = handler.execute(temp_json_path, temp_dir)
                        doc.mime_plugins_result += f"{handler.name}:\n{stderr}\n\n"

                        if code != 0:
                            doc.error = f"{doc.error or ''}\nExecution of {handler.name} failed with status {code}:\n{stderr}".strip()
                            crawl_logger.error(f"Mime handler {handler.name} on {doc.url} with code {code}: {stderr}")
                            continue

                        try:
                            try:
                                data = json.loads(stdout)
                            except ValueError as e:
                                doc.error = f"{doc.error or ''}\n{handler.name} output is not valid JSON: {e}\ncontent: {stdout[:1000]}"
                                crawl_logger.error(
                                    f"Mime handler {handler.name} output is not valid JSON on {doc.url}: {e}\ncontent: {stdout[:1000]}"
                                )
                                continue

                            if stdout:
                                preview = None
                                if "preview" in data:
                                    preview = data.pop("preview")
                                    preview_file = os.path.join(temp_dir, preview)
                                    if os.path.exists(preview_file):
                                        with Image.open(preview_file) as img:
                                            # Remove alpha channel from the png
                                            img = img.convert("RGB")
                                            img.thumbnail((160, 100))
                                            thumb_jpg = os.path.join(
                                                settings.SOSSE_THUMBNAILS_DIR, doc.image_name() + ".jpg"
                                            )
                                            dir_name = os.path.dirname(thumb_jpg)
                                            os.makedirs(dir_name, exist_ok=True)
                                            img.save(thumb_jpg, "jpeg")
                                    else:
                                        raise Exception(f"Preview file {preview} does not exist")
                                serializer = DocumentSerializer(doc, data=data, partial=True)
                                serializer.is_valid(raise_exception=True)
                                serializer.update(doc, serializer.validated_data)
                                if preview:
                                    doc.has_thumbnail = True
                        except Exception as e:
                            doc.error = f"{doc.error or ''}\n{handler.name} processing error: {e}".strip()
                            doc.mime_plugins_result += f"{handler.name}:\n{stderr}\n\n"
                            crawl_logger.error(f"Mime handler {handler.name} processing error on {doc.url}: {e}")
                            if getattr(settings, "TEST_MODE", False):
                                raise
                            continue
        finally:
            if temp_json_path and os.path.exists(temp_json_path):
                os.remove(temp_json_path)
            if temp_content_path and os.path.exists(temp_content_path):
                os.remove(temp_content_path)

    def __str__(self):
        return self.name
