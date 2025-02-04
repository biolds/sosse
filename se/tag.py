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

from colorsys import hsv_to_rgb
from itertools import groupby

from django.db import models
from mptt.models import MPTTModel, TreeForeignKey


class Tag(MPTTModel):
    name = models.CharField(max_length=50, unique=True)
    parent = TreeForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")

    class MPTTMeta:
        order_insertion_by = ["name"]

    def __str__(self):
        return self.name

    @staticmethod
    def _from_palette(val):
        saturation = 0.5
        value = 0.9

        color = hsv_to_rgb(val, saturation, value)
        return tuple(int(255 * c) for c in color)

    def _color(self):
        root_tag_count = Tag.objects.filter(parent=None).count()
        root = self.get_root()
        value = ((root.tree_id - 1) / root_tag_count) + (
            (self.lft - root.lft) / (root.rght - root.lft) / root_tag_count * 0.6  # make a gap between top categories
        )

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
        return 20 * self.level

    def path_name(self):
        ancestors = self.get_ancestors(include_self=True)
        return " › ".join(ancestors.values_list("name", flat=True))

    def js_add_tag_onclick(self):
        return f"switch_tag({self.pk})"

    # Copied from mptt.managers.TreeManager
    @classmethod
    def _get_queryset_relatives(cls, queryset, direction, include_self):
        """Returns a queryset containing either the descendants ``direction ==
        desc`` or the ancestors ``direction == asc`` of a given queryset.

        This function is not meant to be called directly, although there is no
        harm in doing so.

        Instead, it should be used via ``get_queryset_descendants()`` and/or
        ``get_queryset_ancestors()``.

        This function works by grouping contiguous siblings and using them to create
        a range that selects all nodes between the range, instead of querying for each
        node individually. Three variables are required when querying for ancestors or
        descendants: tree_id_attr, left_attr, right_attr. If we weren't using ranges
        and our queryset contained 100 results, the resulting SQL query would contain
        300 variables. However, when using ranges, if the same queryset contained 10
        sets of contiguous siblings, then the resulting SQL query should only contain
        30 variables.

        The attributes used to create the range are completely
        dependent upon whether you are ascending or descending the tree.

        * Ascending (ancestor nodes): select all nodes whose right_attr is greater
          than (or equal to, if include_self = True) the smallest right_attr within
          the set of contiguous siblings, and whose left_attr is less than (or equal
          to) the largest left_attr within the set of contiguous siblings.

        * Descending (descendant nodes): select all nodes whose left_attr is greater
          than (or equal to, if include_self = True) the smallest left_attr within
          the set of contiguous siblings, and whose right_attr is less than (or equal
          to) the largest right_attr within the set of contiguous siblings.

        The result is the more contiguous siblings in the original queryset, the fewer
        SQL variables will be required to execute the query.
        """
        if not cls == queryset.model:
            raise Exception("Parameter 'queryset' must be a queryset of the model")

        opts = queryset.model._mptt_meta

        filters = models.Q()

        e = "e" if include_self else ""
        max_op = "lt" + e
        min_op = "gt" + e
        if direction == "asc":
            max_attr = opts.left_attr
            min_attr = opts.right_attr
        elif direction == "desc":
            max_attr = opts.right_attr
            min_attr = opts.left_attr

        tree_key = opts.tree_id_attr
        min_key = f"{min_attr}__{min_op}"
        max_key = f"{max_attr}__{max_op}"

        q = queryset.order_by(opts.tree_id_attr, opts.parent_attr, opts.left_attr).only(
            opts.tree_id_attr,
            opts.left_attr,
            opts.right_attr,
            min_attr,
            max_attr,
            opts.parent_attr,
            # These fields are used by MPTTModel.update_mptt_cached_fields()
            *[f.lstrip("-") for f in opts.order_insertion_by],
        )

        if not q:
            if hasattr(cls, "objects"):
                return cls.objects.none()
            return cls.none()

        for group in groupby(
            q,
            key=lambda n: (
                getattr(n, opts.tree_id_attr),
                getattr(n, opts.parent_attr + "_id"),
            ),
        ):
            next_lft = None
            for node in list(group[1]):
                tree, lft, rght, min_val, max_val = (
                    getattr(node, opts.tree_id_attr),
                    getattr(node, opts.left_attr),
                    getattr(node, opts.right_attr),
                    getattr(node, min_attr),
                    getattr(node, max_attr),
                )
                if next_lft is None:
                    next_lft = rght + 1
                    min_max = {"min": min_val, "max": max_val}
                elif lft == next_lft:
                    if min_val < min_max["min"]:
                        min_max["min"] = min_val
                    if max_val > min_max["max"]:
                        min_max["max"] = max_val
                    next_lft = rght + 1
                elif lft != next_lft:
                    filters |= models.Q(
                        **{
                            tree_key: tree,
                            min_key: min_max["min"],
                            max_key: min_max["max"],
                        }
                    )
                    min_max = {"min": min_val, "max": max_val}
                    next_lft = rght + 1
            filters |= models.Q(
                **{
                    tree_key: tree,
                    min_key: min_max["min"],
                    max_key: min_max["max"],
                }
            )

        return cls.objects.filter(filters)

    # Copied from mptt.managers.TreeManager
    @classmethod
    def get_queryset_descendants(cls, queryset, include_self=False):
        """Returns a queryset containing the descendants of all nodes in the
        given queryset.

        If ``include_self=True``, nodes in ``queryset`` will also
        be included in the result.
        """
        return cls._get_queryset_relatives(queryset, "desc", include_self)

    # Copied from mptt.managers.TreeManager
    @classmethod
    def get_queryset_ancestors(cls, queryset, include_self=False):
        """Returns a queryset containing the ancestors of all nodes in the
        given queryset.

        If ``include_self=True``, nodes in ``queryset`` will also
        be included in the result.
        """
        return cls._get_queryset_relatives(queryset, "asc", include_self)
