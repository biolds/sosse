"""osse URL Configuration

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
from django.urls import path, re_path
from se.views import favicon, history, prefs, search, word_stats
from se.atom import atom
from se.screenshot import screenshot
from se.stats import stats
from se.www import www

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', search, name='search'),
    path('prefs/', prefs),
    path('stats/', stats),
    path('atom/', atom),
    path('word_stats/', word_stats),
    path('history/', history, name='history'),
    re_path(r'favicon/(?P<favicon_id>[0-9]+)', favicon, name='favicon'),
    re_path(r'screenshot/(?P<url>.*)', screenshot, name='screenshot'),
    re_path(r'www/(?P<url>.*)', www, name='www')
]
