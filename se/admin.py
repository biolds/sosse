from django.contrib import admin

from .models import Document, QueueWhitelist, UrlQueue

admin.site.register(Document)
admin.site.register(QueueWhitelist)
admin.site.register(UrlQueue)
