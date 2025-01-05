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

from django.utils.decorators import method_decorator

from .login import login_required
from .models import Document
from .views import UserView


@method_decorator(login_required, name="dispatch")
class PreferencesView(UserView):
    template_name = "se/prefs.html"
    title = "Preferences"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context | {"supported_langs": json.dumps(Document.get_supported_lang_dict())}