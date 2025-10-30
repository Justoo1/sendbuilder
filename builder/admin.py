from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    User, DetectedDomain, Study, StudyContent, ExtractedDomain, FDAFile, Domain,
    DomainDetectionPrompt, DomainExtractionPrompt, StudySubmission, ExtractedField,
    ReviewComment, AICorrection, DataProvenance
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin with role-based fields"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_available', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'is_available')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        (_('Role & Specialization'), {'fields': ('role', 'department', 'specialization', 'is_available')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_available'),
        }),
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'department')
    ordering = ('username',)


@admin.register(StudySubmission)
class StudySubmissionAdmin(admin.ModelAdmin):
    """Admin for workflow submission management"""
    list_display = ('submission_id', 'study', 'status', 'priority', 'created_at', 'updated_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('submission_id', 'study__study_number', 'study__title')
    readonly_fields = ('submission_id', 'uploaded_at', 'created_at', 'updated_at',
                      'ai_processing_started_at', 'ai_processing_completed_at',
                      'tox_review_started_at', 'tox_review_completed_at',
                      'send_review_started_at', 'send_review_completed_at',
                      'qc_review_started_at', 'qc_review_completed_at',
                      'approved_at', 'rejected_at')

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('submission_id', 'study', 'status', 'priority')
        }),
        (_('Reviewer Assignments'), {
            'fields': ('assigned_toxicologist', 'assigned_send_expert', 'assigned_qc_reviewer')
        }),
        (_('Workflow Timestamps'), {
            'fields': (
                ('uploaded_at', 'ai_processing_started_at', 'ai_processing_completed_at'),
                ('tox_review_started_at', 'tox_review_completed_at'),
                ('send_review_started_at', 'send_review_completed_at'),
                ('qc_review_started_at', 'qc_review_completed_at'),
                ('approved_at', 'rejected_at')
            ),
            'classes': ('collapse',)
        }),
        (_('Notes & Rejection'), {
            'fields': ('notes', 'rejection_reason')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('study', 'assigned_toxicologist', 'assigned_send_expert', 'assigned_qc_reviewer')


@admin.register(ExtractedField)
class ExtractedFieldAdmin(admin.ModelAdmin):
    """Admin for extracted field management with confidence scoring"""
    list_display = ('submission', 'domain', 'variable', 'value', 'confidence_score',
                   'requires_review', 'reviewed', 'is_corrected')
    list_filter = ('domain', 'requires_review', 'reviewed', 'is_corrected', 'created_at')
    search_fields = ('submission__submission_id', 'domain', 'variable', 'value')
    readonly_fields = ('original_value', 'created_at', 'updated_at')

    fieldsets = (
        (_('Field Information'), {
            'fields': ('submission', 'domain', 'variable')
        }),
        (_('Values'), {
            'fields': ('value', 'original_value', 'confidence_score')
        }),
        (_('Review Status'), {
            'fields': ('requires_review', 'reviewed', 'reviewed_by', 'reviewed_at', 'is_corrected')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('submission', 'reviewed_by')


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    """Admin for review comments management"""
    list_display = ('submission', 'reviewer', 'domain', 'severity', 'resolved', 'created_at')
    list_filter = ('severity', 'resolved', 'created_at', 'domain')
    search_fields = ('submission__submission_id', 'reviewer__username', 'comment')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at')

    fieldsets = (
        (_('Comment Information'), {
            'fields': ('submission', 'reviewer', 'domain', 'variable', 'comment', 'severity')
        }),
        (_('Resolution'), {
            'fields': ('resolved', 'resolved_by', 'resolved_at', 'resolution_notes')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('submission', 'reviewer', 'resolved_by')


@admin.register(AICorrection)
class AICorrectionAdmin(admin.ModelAdmin):
    """Admin for AI corrections tracking"""
    list_display = ('submission', 'domain', 'variable', 'corrected_by', 'correction_type',
                   'added_to_training', 'created_at')
    list_filter = ('domain', 'correction_type', 'added_to_training', 'created_at')
    search_fields = ('submission__submission_id', 'domain', 'variable', 'original_extraction', 'corrected_value')
    readonly_fields = ('created_at', 'updated_at', 'training_export_date')

    fieldsets = (
        (_('Correction Information'), {
            'fields': ('submission', 'domain', 'variable', 'corrected_by', 'correction_type')
        }),
        (_('Values'), {
            'fields': ('original_extraction', 'corrected_value', 'correction_reason', 'ai_confidence_before')
        }),
        (_('Training Data'), {
            'fields': ('added_to_training', 'training_export_date')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('submission', 'corrected_by')

    actions = ['mark_as_training_data']

    def mark_as_training_data(self, request, queryset):
        """Mark selected corrections as training data"""
        count = 0
        for correction in queryset:
            if not correction.added_to_training:
                correction.mark_as_training_data()
                count += 1
        self.message_user(request, f'{count} correction(s) marked as training data.')
    mark_as_training_data.short_description = "Mark selected as training data"


@admin.register(DataProvenance)
class DataProvenanceAdmin(admin.ModelAdmin):
    """Admin for data provenance tracking"""
    list_display = ('submission', 'domain', 'variable', 'pdf_page', 'extraction_method',
                   'extracted_by', 'reviewed_by')
    list_filter = ('domain', 'extraction_method', 'pdf_page', 'extracted_at')
    search_fields = ('submission__submission_id', 'domain', 'variable', 'value')
    readonly_fields = ('extracted_at', 'reviewed_at', 'created_at', 'updated_at')

    fieldsets = (
        (_('Data Information'), {
            'fields': ('submission', 'domain', 'variable', 'value', 'confidence_score')
        }),
        (_('PDF Source'), {
            'fields': ('pdf_page', 'pdf_table', 'pdf_row', 'pdf_column', 'pdf_coordinates', 'source_text')
        }),
        (_('Extraction Details'), {
            'fields': ('extraction_method', 'extracted_by', 'extracted_at')
        }),
        (_('Review Details'), {
            'fields': ('reviewed_by', 'reviewed_at')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('submission', 'extracted_by', 'reviewed_by')


# Register existing models with basic admin
admin.site.register(DetectedDomain)
admin.site.register(Study)
admin.site.register(StudyContent)
admin.site.register(ExtractedDomain)
admin.site.register(FDAFile)
admin.site.register(Domain)
admin.site.register(DomainDetectionPrompt)
admin.site.register(DomainExtractionPrompt)

# Customize admin site header
admin.site.site_header = "SEND Builder Administration"
admin.site.site_title = "SEND Builder Admin"
admin.site.index_title = "Welcome to SEND Builder Administration"
