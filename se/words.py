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

from django.views.generic import TemplateView

from .archive import ArchiveMixin


class WordsView(ArchiveMixin, TemplateView):
    template_name = "se/words.html"
    view_name = "words"

    def get_context_data(self, *args, **kwargs):
        words = []
        for w in self.doc.vector.split():
            word, weights = w.split(":", 1)
            word = word.strip("'")
            words.append((word, weights))

        context = super().get_context_data(*args, **kwargs)
        return context | {"words": words, "lang": self.doc.lang_flag(True)}
