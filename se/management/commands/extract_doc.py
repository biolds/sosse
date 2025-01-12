# Copyright 2022-2025 Laurent Defert
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

import base64
import json
import os
import unicodedata
from argparse import ArgumentParser

from django.conf import settings
from django.core.management import get_commands, load_command_class
from django.core.management.base import BaseCommand

from sosse.conf import DEFAULTS as DEFAULT_CONF

from .update_se import SE_FILE

SECTIONS = [
    [
        "common",
        "This section describes options common to the web interface and the crawlers.",
    ],
    ["webserver", "This section describes options dedicated to the web interface."],
    ["crawler", "This section describes options dedicated to the web interface."],
]


EXAMPLE_SEARCH_STR = "SOSSE"


def unicode_len(s):
    _len = 0
    for c in s:
        _len += 1
        if unicodedata.name(c).startswith("CJK UNIFIED IDEOGRAPH"):
            _len += 1
    return _len


def unicode_justify(s, _len):
    return s + " " * (_len - unicode_len(s))


class Command(BaseCommand):
    help = "Displays code-defined documentation on stdout."

    def add_arguments(self, parser):
        parser.add_argument(
            "component",
            choices=["conf", "cli", "se"],
            help='"conf" for the configuration file,\n"cli" for the CLI,\n"se" for search engines',
        )

    def handle(self, *args, **options):
        if options["component"] == "conf":
            for section, descr in SECTIONS:
                section_title = f"[{section}] section"
                self.stdout.write(section_title)
                self.stdout.write("-" * len(section_title))
                self.stdout.write()
                self.stdout.write(descr)
                self.stdout.write()
                for name, conf in DEFAULT_CONF[section].items():
                    self.stdout.write(f".. _conf_option_{name}:")
                    self.stdout.write()
                    self.stdout.write(f".. describe:: {name}")
                    self.stdout.write()
                    default = conf.default
                    if default is None or default == "":
                        default = "<empty>"
                    self.stdout.write(f"   *Default: {default}*")
                    self.stdout.write()
                    comment = conf.doc or conf.comment
                    comment = "\n".join("   " + line for line in comment.splitlines())
                    comment = comment.replace("\n   See ", "\n\n   See ")
                    if comment:
                        self.stdout.write(comment)
                    self.stdout.write(".. raw:: html")
                    self.stdout.write()
                    self.stdout.write("   <br/>")
                    self.stdout.write()
        elif options["component"] == "cli":
            has_content = False
            for cmd, mod in sorted(get_commands().items(), key=lambda x: x[0]):
                if mod != "se":
                    continue
                has_content = True
                klass = load_command_class("se", cmd)
                parser = ArgumentParser()
                klass.add_arguments(parser)

                self.stdout.write(f".. _cli_{cmd}:")
                self.stdout.write()
                self.stdout.write(f".. describe:: {cmd}:")

                txt = getattr(klass, "doc", klass.help)
                txt = [""] + [line[4:] if line.startswith(" " * 4) else line for line in txt.splitlines()] + [""]
                txt = "\n   ".join(txt)
                self.stdout.write(txt)

                self.stdout.write(".. code-block:: text")
                self.stdout.write()
                usage = [""] + parser.format_help().splitlines()
                usage = "\n   ".join(usage)
                usage = usage.replace("sosse_admin.py", f"sosse-admin {cmd}")
                self.stdout.write(usage)

                self.stdout.write(".. raw:: html")
                self.stdout.write()
                self.stdout.write("   <br/>")
                self.stdout.write()
            if not has_content:
                raise Exception("Failed")
        elif options["component"] == "se":
            se_file = os.path.join(settings.BASE_DIR, SE_FILE)
            with open(se_file) as f:
                search_engines = json.load(f)
            search_engines = [entry["fields"] for entry in search_engines]
            SE_STR = "**Search Engine**"
            SC_STR = "**Shortcut example**"
            se_len = unicode_len(SE_STR)
            sc_len = unicode_len(SC_STR) + 1
            for se in search_engines:
                name = se["long_name"] or se["short_name"]
                se["name"] = name
                url = se["html_template"]
                url = url.replace("{searchTerms}", EXAMPLE_SEARCH_STR.replace(" ", "%20"))
                url = url.replace(
                    "{searchTermsBase64}",
                    base64.b64encode(EXAMPLE_SEARCH_STR.encode("utf-8")).decode("utf-8"),
                )
                url = f"`{settings.SOSSE_SEARCH_SHORTCUT_CHAR}{se['shortcut']} {EXAMPLE_SEARCH_STR} <{url}>`_"
                se["shortcut"] = url

                se_len = max(se_len, unicode_len(name))
                sc_len = max(sc_len, unicode_len(se["shortcut"]))

            self.stdout.write(".. table::")
            self.stdout.write("   :align: left")
            self.stdout.write("   :widths: auto")
            self.stdout.write()
            self.stdout.write("   " + "=" * se_len + "  " + "=" * sc_len)
            self.stdout.write("   " + SE_STR.ljust(se_len) + "  " + SC_STR.ljust(sc_len))
            self.stdout.write("   " + "=" * se_len + "  " + "=" * sc_len)

            search_engines = sorted(search_engines, key=lambda x: x["name"])

            for se in search_engines:
                self.stdout.write(
                    "   " + unicode_justify(se["name"], se_len) + "  " + unicode_justify(se["shortcut"], sc_len)
                )
            self.stdout.write("   " + "=" * se_len + "  " + "=" * sc_len)
            self.stdout.write()
            self.stdout.write()
