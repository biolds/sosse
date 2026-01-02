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

from rest_framework import routers

from .add_to_queue import AddToQueueViewSet
from .collection import CollectionViewSet
from .cookie import CookieViewSet
from .crawler_stats import CrawlerStatsViewSet
from .hdd_stats import HddStatsViewSet
from .lang_stats import LangStatsViewSet
from .mime_plugin import MimePluginViewSet
from .mime_stats import MimeStatsViewSet
from .profile import ProfileViewSet
from .search import SearchViewSet
from .tag import TagViewSet
from .webhook import WebhookViewSet

router = routers.DefaultRouter()
router.register("tag", TagViewSet)
router.register("search", SearchViewSet, basename="search")
router.register("stats", CrawlerStatsViewSet)
router.register("hdd_stats", HddStatsViewSet, basename="hdd_stats")
router.register("lang_stats", LangStatsViewSet, basename="lang_stats")
router.register("mime_stats", MimeStatsViewSet, basename="mime_stats")
router.register("mime_plugin", MimePluginViewSet)
router.register("webhook", WebhookViewSet, basename="webhook")
router.register("collection", CollectionViewSet, basename="collection")
router.register("queue", AddToQueueViewSet, basename="queue")
router.register("profile", ProfileViewSet, basename="profile")
router.register("cookie", CookieViewSet)
