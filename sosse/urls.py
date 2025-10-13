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
"""Sosse URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from se.about import AboutView
from se.archive import ArchiveRedirectView
from se.atom import AtomView
from se.csv import CsvView
from se.download import DownloadView
from se.favicon import FavIconView
from se.history import HistoryView
from se.html import HTMLExcludedView, HTMLView
from se.login import SELoginView
from se.online import OnlineCheckView
from se.opensearch import OpensearchView
from se.profile import ProfileView
from se.resources import ResourcesView
from se.rest_api import router
from se.screenshot import ScreenshotFullView, ScreenshotView
from se.search import SearchView
from se.search_redirect import SearchRedirectView
from se.tags import AdminTagsView, ArchiveTagsView, SearchTagsView
from se.tags_list import TagsListView
from se.words import WordsView
from se.www import WWWView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", SearchView.as_view(), name="search"),
    path("about/", AboutView.as_view(), name="about"),
    path("s/", SearchRedirectView.as_view(), name="search_redirect"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("resources/", ResourcesView.as_view(), name="resources"),
    path("atom/", AtomView.as_view(), name="atom"),
    path("csv/", CsvView.as_view(), name="csv"),
    path("online_check/", OnlineCheckView.as_view(), name="online_check"),
    path("history/", HistoryView.as_view(), name="history"),
    path("login/", SELoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("opensearch.xml", OpensearchView.as_view(), name="opensearch"),
    path("api-auth/", include("rest_framework.urls")),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    re_path(r"^favicon/(?P<favicon_id>[0-9]+)", FavIconView.as_view(), name="favicon"),
    re_path(r"^html/.*", HTMLView.as_view(), name=HTMLView.view_name),
    re_path(r"^screenshot/.*", ScreenshotView.as_view(), name=ScreenshotView.view_name),
    re_path(r"^screenshot_full/.*", ScreenshotFullView.as_view(), name="screenshot_full"),
    re_path(r"^www/.*", WWWView.as_view(), name=WWWView.view_name),
    re_path(r"^words/.*", WordsView.as_view(), name=WordsView.view_name),
    re_path(r"^archive/.*", ArchiveRedirectView.as_view(), name="archive"),
    re_path(r"^download/.*", DownloadView.as_view(), name=DownloadView.view_name),
    path("search_tags/", SearchTagsView.as_view(), name="search_tags"),
    re_path(r"^admin_tags/(?P<model>[a-z]+)/(?P<pk>[0-9]+)/", AdminTagsView.as_view(), name="admin_tags"),
    re_path(r"^archive_tags/(?P<pk>[0-9]+)/", ArchiveTagsView.as_view(), name="archive_tags"),
    re_path(r"^tags_list/(?P<model>[a-z]+)/(?P<pk>[0-9]+)/", TagsListView.as_view(), name="tags_list"),
    re_path(
        r"^html_excluded/(?P<collection>[0-9]+)/(?P<method>url|mime|element)$",
        HTMLExcludedView.as_view(),
        name="html_excluded",
    ),
]
