from django.contrib import admin

from .models import Document, UrlQueue

admin.site.register(Document)
admin.site.register(UrlQueue)
