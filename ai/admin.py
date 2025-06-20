from django.contrib import admin

from .models import AIModel, AIConfiguration

admin.site.register(AIModel)
admin.site.register(AIConfiguration)
