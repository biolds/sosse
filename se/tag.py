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

from colorsys import hsv_to_rgb

from django.db import models, transaction
from treebeard.mp_tree import MP_Node, MP_NodeManager

from .utils import human_nb


class TagManager(MP_NodeManager):
    @transaction.atomic
    def get_or_create(self, defaults=None, **kwargs):
        try:
            return Tag.objects.get(**kwargs), False
        except Tag.DoesNotExist:
            defaults = defaults or {}
            return Tag.add_root(**kwargs, **defaults), True

    @transaction.atomic
    def create(self, **kwargs):
        if "parent" in kwargs:
            parent = kwargs.pop("parent")
            tag = parent.add_child(**kwargs)
        else:
            tag = Tag.add_root(**kwargs)
        return tag


class Tag(MP_Node):
    node_order_by = ["name"]
    objects = TagManager()

    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name

    @staticmethod
    def tree_doc_counts():
        from .document import Document

        all_tags = list(Tag.get_tree())
        tag_to_count = {}

        for tag in reversed(all_tags):
            docs = Document.objects.wo_content().filter(tags=tag.pk)

            # Exclude documents that are tagged with any of the descendants of the current tags
            # This is to avoid counting documents that are tagged with both the current tag and its
            # descendants
            descendant_ids = tag.get_descendants().values_list("pk", flat=True)
            if descendant_ids:
                docs = docs.exclude(tags__in=descendant_ids)

            tag_to_count[tag.pk] = docs.distinct().count()

        _total_counts = dict(tag_to_count)

        for tag in reversed(all_tags):
            parent = tag.get_parent()
            if parent:
                _total_counts[parent.pk] = _total_counts.get(parent.pk, 0) + _total_counts.get(tag.pk, 0)

        total_counts = {}
        for tag_pk, count in _total_counts.items():
            total_counts[tag_pk] = {
                "count": count,
                "human_count": human_nb(count),
            }
        return total_counts

    @staticmethod
    def _from_palette(val):
        saturation = 0.5
        value = 0.9
        color = hsv_to_rgb(val, saturation, value)
        return tuple(int(255 * c) for c in color)

    def _root_index(self):
        segment = self.path[: self.steplen]
        base = len(self.alphabet)
        index = 0
        for char in segment:
            index = index * base + self.alphabet.index(char)
        return index

    def _color(self):
        tag_count = Tag.get_root_nodes().count()
        value = (self._root_index() % tag_count) / tag_count
        return self._from_palette(value)

    def get_color(self):
        return "#%02x%02x%02x" % self._color()

    def _luminance(self):
        r, g, b = self._color()
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def get_text_color(self):
        return "var(--text)" if self._luminance() >= 128 else "var(--bg)"

    def get_bg_color(self):
        return "var(--text)" if self._luminance() < 128 else "var(--bg)"

    def tree_padding(self):
        return 20 * (self.depth - 1)

    def path_name(self):
        ancestors = self.get_ancestors()
        return " › ".join([a.name for a in ancestors] + [self.name])

    def js_add_tag_onclick(self):
        return f"switch_tag({self.pk})"
