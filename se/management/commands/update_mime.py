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

from ...mime_plugin import MimePlugin
from ..builtin import UpdateBuiltinModel


class Command(UpdateBuiltinModel):
    help = "Updates MIME handler definitions."
    doc = "This updates MIME handlers in the database based on their definition in the filesystem."

    json_file = "sosse/mime_plugins.json"
    model_class = MimePlugin
    lookup_field = "name"
    model_name = "MIME handlers"
    fields_to_remove = {"dependencies"}
