# Copyright 2022-2025 Laurent Defert
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

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
from html import unescape
from urllib.parse import quote

project = "Sosse"
copyright = "2022-2025, Laurent Defert"
author = "Laurent Defert"
release = "1.14"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

sys.path.append(os.path.abspath("_extensions"))
extensions = ["code_blocks", "myst_parser"]
test_code_output = "code_blocks.json"

linkcheck_ignore = [
    r"http://192\.168\.0\.1:8080/",
    r"http://127\.0\.0\.1:8005/",
]
linkcheck_retries = 3
linkcheck_timeout = 60

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
html_logo = "../../se/static/se/logo.svg"
html_favicon = "../../se/static/se/logo.svg"
html_css_files = ["style.css"]

html_context = {
    "uma_script": '<script defer src="https://uma.sosse.io/script.js" data-website-id="7650cdb0-7390-41fd-a023-2f9d5c480b6e"></script>',
    # Edit the doc button
    "theme_top_of_page_button": "edit",
    "github_user": "biolds",
    "github_repo": "sosse",
    "github_version": "main",
    "conf_py_path": "/doc/source/",
    # Discussion link
    "discussion_url": "https://github.com/biolds/sosse/discussions",
}


def add_title_quoted(app, pagename, templatename, context, doctree):
    title = context.get("title", "")
    title = unescape(title)
    title = title.encode("ascii", "ignore").decode("ascii")  # remove non-ascii characters
    title = title.strip()
    context["title_quoted"] = quote(title, safe="")


def setup(app):
    app.connect("html-page-context", add_title_quoted)
