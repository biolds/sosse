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
from django.urls import path, re_path
from se.views import about, favicon, history, opensearch, prefs, search, search_redirect, word_stats, SELoginView
from se.atom import atom
from se.cached import cache_redirect
from se.screenshot import screenshot
from se.stats import stats
from se.words import words
from se.www import www

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', search, name='search'),
    path('about/', about, name='about'),
    path('s/', search_redirect, name='search_redirect'),
    path('prefs/', prefs),
    path('stats/', stats),
    path('atom/', atom),
    path('word_stats/', word_stats),
    path('history/', history, name='history'),
    path('login/', SELoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('opensearch.xml', opensearch, name='opensearch'),
    re_path(r'favicon/(?P<favicon_id>[0-9]+)', favicon, name='favicon'),
    re_path(r'screenshot/.*', screenshot, name='screenshot'),
    re_path(r'www/.*', www, name='www'),
    re_path(r'words/.*', words, name='words'),
    re_path(r'cache/.*', cache_redirect, name='cache'),
]
