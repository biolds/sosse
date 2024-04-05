# Copyright 2022-2023 Laurent Defert
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

"""sosse URL Configuration

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

from se.views import about, favicon, history, opensearch, prefs, search, search_redirect, stats, word_stats, SELoginView
from se.atom import atom
from se.cached import cache_redirect
from se.html import html, html_excluded
from se.online import online_check
from se.rest_api import router
from se.screenshot import screenshot, screenshot_full
from se.words import words
from se.www import www

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', search, name='search'),
    path('about/', about, name='about'),
    path('s/', search_redirect, name='search_redirect'),
    path('prefs/', prefs),
    path('stats/', stats, name='stats'),
    path('atom/', atom),
    path('online_check/', online_check, name='online_check'),
    path('word_stats/', word_stats),
    path('history/', history, name='history'),
    path('login/', SELoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('opensearch.xml', opensearch, name='opensearch'),
    path('api-auth/', include('rest_framework.urls')),
    path('api/', include(router.urls)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    re_path(r'^favicon/(?P<favicon_id>[0-9]+)', favicon, name='favicon'),
    re_path(r'^html/.*', html, name='html'),
    re_path(r'^screenshot/.*', screenshot, name='screenshot'),
    re_path(r'^screenshot_full/.*', screenshot_full, name='screenshot_full'),
    re_path(r'^www/.*', www, name='www'),
    re_path(r'^words/.*', words, name='words'),
    re_path(r'^cache/.*', cache_redirect, name='cache'),
    re_path(r'^html_excluded/(?P<crawl_policy>[0-9]+)/(?P<method>url|mime|element)$', html_excluded, name='html_excluded'),
]
