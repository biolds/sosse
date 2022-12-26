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
    re_path(r'screenshot/(?P<url>.*)', screenshot, name='screenshot'),
    re_path(r'www/(?P<url>.*)', www, name='www'),
    re_path(r'words/(?P<url>.*)', words, name='words')
]
