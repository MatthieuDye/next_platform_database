from django.contrib import admin

from .models import Pipeline, RefGenome, LabInfo

admin.site.register(Pipeline)
admin.site.register(LabInfo)
admin.site.register(RefGenome)