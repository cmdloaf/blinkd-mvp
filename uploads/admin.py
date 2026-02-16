from django.contrib import admin

from .models import AnalysisResult, ProductFlow, Screenshot

admin.site.register(ProductFlow)
admin.site.register(Screenshot)
admin.site.register(AnalysisResult)
