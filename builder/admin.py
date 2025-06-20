from django.contrib import admin

from .models import DetectedDomain,Study, StudyContent, ExtractedDomain, FDAFile, Domain, DomainDetectionPrompt, DomainExtractionPrompt

admin.site.register(DetectedDomain)
admin.site.register(Study)
admin.site.register(StudyContent)
admin.site.register(ExtractedDomain)
admin.site.register(FDAFile)
admin.site.register(Domain)
admin.site.register(DomainDetectionPrompt)
admin.site.register(DomainExtractionPrompt)
