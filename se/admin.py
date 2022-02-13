from django.contrib import admin

from .models import Document, QueueWhitelist, UrlQueue, AuthMethod, AuthField, AuthDynamicField

admin.site.register(Document)
admin.site.register(QueueWhitelist)
admin.site.register(UrlQueue)

admin.site.register(AuthMethod)
admin.site.register(AuthField)
admin.site.register(AuthDynamicField)
