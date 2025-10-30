import os
from datetime import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


def xpt_file_path(instance, filename):
    """Generate a path for xpt files"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return os.path.join('xpt_files', timestamp, filename)

def study_file_path(instance, filename):
    """Generate a path for study files"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return os.path.join('study_files', timestamp, filename)

def fda_document_path(instance, filename):
    """Generate a path for fda files"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return os.path.join('fda_documents', timestamp, filename)

class Study(models.Model):
    """
    Study model to store information about a study.
    """
    study_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    study_number = models.CharField(max_length=200)
    study_sponsor = models.CharField(max_length=200)
    study_type = models.CharField(max_length=200)
    species = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField()
    status = models.CharField(max_length=200, default='Draft')
    completed = models.BooleanField(default=False)
    study_file = models.FileField(upload_to=study_file_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Study'
        verbose_name_plural = 'Studies'

    def get_absolute_url(self):
        return f'/studies/{self.id}/'

    def get_edit_url(self):
        return f'/studies/{self.id}/edit/'

    def get_delete_url(self):
        return f'/studies/{self.id}/delete/'
    
    def complete(self):
        self.completed = True
        self.status = 'Completed'
        self.save()

    def in_progress(self):
        self.completed = False
        self.status = 'In Progress'
        self.save()

    def uncomplete(self):
        self.completed = False
        self.status = 'Failed'
        self.save()

class User(AbstractUser):
    """
    Custom User model with role-based access control for SEND validation workflow.
    Extends Django's AbstractUser to add role functionality.
    """

    class UserRole(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrator')
        TOXICOLOGIST = 'TOXICOLOGIST', _('Toxicologist')
        SEND_EXPERT = 'SEND_EXPERT', _('SEND Expert')
        QC_REVIEWER = 'QC_REVIEWER', _('QC Reviewer')

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.TOXICOLOGIST,
        help_text=_('User role for workflow access control')
    )

    email = models.EmailField(
        unique=True,
        help_text=_('Required for workflow notifications')
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_('Optional contact phone number')
    )

    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_('Department or team')
    )

    specialization = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Area of expertise (e.g., Cardiotoxicity, SEND Implementation)')
    )

    is_available = models.BooleanField(
        default=True,
        help_text=_('Whether user is available for new assignments')
    )

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"


class DocumentUpload(models.Model):
    """Model to track uploaded documents"""
    file = models.FileField(upload_to='uploads/')
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey('User', on_delete=models.CASCADE, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.BigIntegerField()
    study = models.ForeignKey(Study, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.original_filename} - {self.uploaded_at}"

class StudyContent(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    content = models.TextField()
    page = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Study Content'
        verbose_name_plural = 'Study Contents'

    def __str__(self):
        return f"{self.study.title} - Page {self.page}"
    
    def get_absolute_url(self):
        return f'/studies/{self.study.study_id}/{self.page}/'
    

class Domain(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=200)
    description = models.TextField()
    icon = models.ImageField(upload_to='icons/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/domains/{self.id}/'

    def get_edit_url(self):
        return f'/domains/{self.id}/edit/'

    def get_delete_url(self):
        return f'/domains/{self.id}/delete/'

class DetectedDomain(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    content_id = models.JSONField()
    page = models.JSONField()
    confident_score = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Deetected Domain'
        verbose_name_plural = 'Deetected Domains'

    def __str__(self):
        return f"{self.domain.name} - Page {self.page}"
    
    def get_absolute_url(self):
        return f'/studies/detected/{self.id}/'

    def get_edit_url(self):
        return f'/studies/detected/{self.id}/edit/'

    def get_delete_url(self):
        return f'/studies/detected/{self.id}/delete/'
    
    def process_content_id(self, content_id):
        content = StudyContent.objects.filter(id=content_id).first()
        if content:
            self.content_id.append(content.id)
            self.save()
        else:
            raise ValueError("Content not found")
        
    def process_page(self, page):
        self.page.append(page)
        self.save()
        
    def process_confident_score(self, confident_score):
        self.confident_score = confident_score
        self.save()


class ExtractedDomain(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    content = models.JSONField() # this will be extracted content saved as list of dictionary
    xpt_file = models.FileField(upload_to=xpt_file_path, blank=True, null=True)
    csv_file = models.FileField(upload_to=xpt_file_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Extracted Domain'
        verbose_name_plural = 'Extracted Domains'

    def __str__(self):
        return f"{self.domain.name}"
    
    def get_absolute_url(self):
        return f'/studies/extracted/{self.id}/'

    def get_edit_url(self):
        return f'/studies/extracted/{self.id}/edit/'

    def get_delete_url(self):
        return f'/studies/extracted/{self.id}/delete/'
    

class FDAFile(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='fda_files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'FDA File'
        verbose_name_plural = 'FDA Files'

    def __str__(self):
        return f"{self.study.title} - FDA File"
    
    def get_absolute_url(self):
        return f'/studies/fda/{self.id}/'

    def get_edit_url(self):
        return f'/studies/fda/{self.id}/edit/'

    def get_delete_url(self):
        return f'/studies/fda/{self.id}/delete/'
    

class DomainDetectionPrompt(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    prompt = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Domain Detection Prompt'
        verbose_name_plural = 'Domain Detection Prompts'

    def __str__(self):
        return self.name
    
    def save_name(self):
        self.name = f"{self.domain.name} - prompt"
        super().save()

    def get_absolute_url(self):
        return f'/studies/prompts/{self.id}/'

    def get_edit_url(self):
        return f'/studies/prompts/{self.id}/edit/'

    def get_delete_url(self):
        return f'/studies/prompts/{self.id}/delete/'
    

class DomainExtractionPrompt(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    prompt = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Domain Extraction Prompt'
        verbose_name_plural = 'Domain Extraction Prompts'

    def __str__(self):
        return self.name
    
    def save_name(self):
        self.name = f"{self.domain.name} - prompt"
        super().save()

    def get_absolute_url(self):
        return f'/studies/extraction/prompts/{self.id}/'

    def get_edit_url(self):
        return f'/studies/extraction/prompts/{self.id}/edit/'

    def get_delete_url(self):
        return f'/studies/extraction/prompts/{self.id}/delete/'


# ======================================================================
# ENHANCED WORKFLOW MODELS FOR MULTI-LAYER VALIDATION SYSTEM
# ======================================================================


class StudySubmission(models.Model):
    """
    Main workflow model tracking study submissions through multi-stage review process.
    Links to existing Study model and manages workflow state transitions.
    """

    class Status(models.TextChoices):
        UPLOADED = 'UPLOADED', _('Uploaded')
        AI_PROCESSING = 'AI_PROCESSING', _('AI Processing')
        TOXICOLOGIST_REVIEW = 'TOXICOLOGIST_REVIEW', _('Toxicologist Review')
        SEND_EXPERT_REVIEW = 'SEND_EXPERT_REVIEW', _('SEND Expert Review')
        QC_REVIEW = 'QC_REVIEW', _('QC Review')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

    study = models.OneToOneField(
        Study,
        on_delete=models.CASCADE,
        related_name='submission',
        help_text=_('Linked study instance')
    )

    submission_id = models.CharField(
        max_length=50,
        unique=True,
        help_text=_('Unique submission identifier')
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.UPLOADED,
        help_text=_('Current workflow status')
    )

    # Reviewer assignments
    assigned_toxicologist = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tox_reviews',
        limit_choices_to={'role': 'TOXICOLOGIST'},
        help_text=_('Assigned toxicologist for scientific review')
    )

    assigned_send_expert = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='send_reviews',
        limit_choices_to={'role': 'SEND_EXPERT'},
        help_text=_('Assigned SEND expert for compliance review')
    )

    assigned_qc_reviewer = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qc_reviews',
        limit_choices_to={'role': 'QC_REVIEWER'},
        help_text=_('Assigned QC reviewer for final quality check')
    )

    # Workflow timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    ai_processing_started_at = models.DateTimeField(null=True, blank=True)
    ai_processing_completed_at = models.DateTimeField(null=True, blank=True)
    tox_review_started_at = models.DateTimeField(null=True, blank=True)
    tox_review_completed_at = models.DateTimeField(null=True, blank=True)
    send_review_started_at = models.DateTimeField(null=True, blank=True)
    send_review_completed_at = models.DateTimeField(null=True, blank=True)
    qc_review_started_at = models.DateTimeField(null=True, blank=True)
    qc_review_completed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    priority = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('Priority level (1=Critical, 5=Low)')
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text=_('Reason for rejection if status is REJECTED')
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text=_('General notes about the submission')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Study Submission')
        verbose_name_plural = _('Study Submissions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['submission_id']),
        ]

    def __str__(self):
        return f"{self.submission_id} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        """Auto-generate submission_id if not set"""
        if not self.submission_id:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.submission_id = f"SUB-{self.study.study_number}-{timestamp}"
        super().save(*args, **kwargs)

    def can_transition_to(self, new_status):
        """
        Validate if transition to new_status is allowed from current status.
        Implements workflow state machine logic.
        """
        valid_transitions = {
            self.Status.UPLOADED: [self.Status.AI_PROCESSING],
            self.Status.AI_PROCESSING: [self.Status.TOXICOLOGIST_REVIEW, self.Status.REJECTED],
            self.Status.TOXICOLOGIST_REVIEW: [self.Status.SEND_EXPERT_REVIEW, self.Status.REJECTED],
            self.Status.SEND_EXPERT_REVIEW: [self.Status.QC_REVIEW, self.Status.TOXICOLOGIST_REVIEW, self.Status.REJECTED],
            self.Status.QC_REVIEW: [self.Status.APPROVED, self.Status.SEND_EXPERT_REVIEW, self.Status.REJECTED],
            self.Status.APPROVED: [],  # Terminal state
            self.Status.REJECTED: [self.Status.TOXICOLOGIST_REVIEW],  # Can restart from toxicologist review
        }
        return new_status in valid_transitions.get(self.status, [])

    def transition_to(self, new_status, user=None, reason=None):
        """
        Transition to new status with validation and timestamp updates.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid transition from {self.get_status_display()} to {self.Status(new_status).label}"
            )

        # Update timestamps based on new status
        now = datetime.now()
        if new_status == self.Status.AI_PROCESSING:
            self.ai_processing_started_at = now
        elif new_status == self.Status.TOXICOLOGIST_REVIEW:
            self.tox_review_started_at = now
        elif new_status == self.Status.SEND_EXPERT_REVIEW:
            if self.status == self.Status.TOXICOLOGIST_REVIEW:
                self.tox_review_completed_at = now
            self.send_review_started_at = now
        elif new_status == self.Status.QC_REVIEW:
            self.send_review_completed_at = now
            self.qc_review_started_at = now
        elif new_status == self.Status.APPROVED:
            self.qc_review_completed_at = now
            self.approved_at = now
        elif new_status == self.Status.REJECTED:
            self.rejected_at = now
            if reason:
                self.rejection_reason = reason

        self.status = new_status
        self.save()
        return True


class ExtractedField(models.Model):
    """
    Enhanced model for individual extracted data fields with confidence scoring.
    Links extracted data points to their source and tracks review status.
    """

    submission = models.ForeignKey(
        StudySubmission,
        on_delete=models.CASCADE,
        related_name='extracted_fields',
        help_text=_('Linked study submission')
    )

    domain = models.CharField(
        max_length=2,
        help_text=_('SEND domain code (e.g., DM, BW, LB)')
    )

    variable = models.CharField(
        max_length=8,
        help_text=_('SEND variable name (e.g., STUDYID, USUBJID)')
    )

    value = models.CharField(
        max_length=200,
        help_text=_('Extracted value')
    )

    original_value = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Original AI-extracted value before any corrections')
    )

    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('AI confidence score (0.0-1.0)')
    )

    requires_review = models.BooleanField(
        default=False,
        help_text=_('Flagged for human review if confidence < 0.85')
    )

    reviewed = models.BooleanField(
        default=False,
        help_text=_('Whether field has been reviewed by human')
    )

    reviewed_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_fields',
        help_text=_('User who reviewed this field')
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Timestamp of review')
    )

    is_corrected = models.BooleanField(
        default=False,
        help_text=_('Whether field was corrected from original extraction')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Extracted Field')
        verbose_name_plural = _('Extracted Fields')
        ordering = ['domain', 'variable']
        indexes = [
            models.Index(fields=['submission', 'domain']),
            models.Index(fields=['requires_review']),
            models.Index(fields=['confidence_score']),
        ]

    def __str__(self):
        return f"{self.domain}.{self.variable} = {self.value} (conf: {self.confidence_score:.2f})"

    def save(self, *args, **kwargs):
        """Auto-flag for review if confidence below threshold"""
        if self.confidence_score < 0.85:
            self.requires_review = True

        # Store original value on first save
        if not self.pk and not self.original_value:
            self.original_value = self.value

        super().save(*args, **kwargs)

    def get_confidence_level(self):
        """Return human-readable confidence level"""
        if self.confidence_score >= 0.90:
            return 'High'
        elif self.confidence_score >= 0.75:
            return 'Medium'
        else:
            return 'Low'

    def get_confidence_color(self):
        """Return Bootstrap color class for confidence level"""
        if self.confidence_score >= 0.90:
            return 'success'
        elif self.confidence_score >= 0.75:
            return 'warning'
        else:
            return 'danger'


class ReviewComment(models.Model):
    """
    Model for tracking reviewer feedback and comments during validation workflow.
    Supports issue tracking, severity levels, and resolution status.
    """

    class Severity(models.TextChoices):
        CRITICAL = 'CRITICAL', _('Critical - Must Fix')
        MAJOR = 'MAJOR', _('Major - Should Fix')
        MINOR = 'MINOR', _('Minor - Optional')
        INFO = 'INFO', _('Informational')

    submission = models.ForeignKey(
        StudySubmission,
        on_delete=models.CASCADE,
        related_name='review_comments',
        help_text=_('Linked study submission')
    )

    reviewer = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='comments_made',
        help_text=_('User who made the comment')
    )

    domain = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        help_text=_('SEND domain code if comment is domain-specific')
    )

    variable = models.CharField(
        max_length=8,
        blank=True,
        null=True,
        help_text=_('SEND variable name if comment is field-specific')
    )

    comment = models.TextField(
        help_text=_('Review comment or feedback')
    )

    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MINOR,
        help_text=_('Severity level of the issue')
    )

    resolved = models.BooleanField(
        default=False,
        help_text=_('Whether issue has been resolved')
    )

    resolved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comments_resolved',
        help_text=_('User who resolved the issue')
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Timestamp of resolution')
    )

    resolution_notes = models.TextField(
        blank=True,
        null=True,
        help_text=_('Notes about how issue was resolved')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Review Comment')
        verbose_name_plural = _('Review Comments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['submission', 'resolved']),
            models.Index(fields=['severity', 'resolved']),
        ]

    def __str__(self):
        domain_info = f" ({self.domain})" if self.domain else ""
        return f"{self.get_severity_display()}{domain_info} by {self.reviewer.get_full_name()}"

    def resolve(self, user, notes=None):
        """Mark comment as resolved"""
        self.resolved = True
        self.resolved_by = user
        self.resolved_at = datetime.now()
        if notes:
            self.resolution_notes = notes
        self.save()

    def get_severity_color(self):
        """Return Bootstrap color class for severity"""
        colors = {
            self.Severity.CRITICAL: 'danger',
            self.Severity.MAJOR: 'warning',
            self.Severity.MINOR: 'info',
            self.Severity.INFO: 'secondary',
        }
        return colors.get(self.severity, 'secondary')


class AICorrection(models.Model):
    """
    Model for tracking human corrections to AI extractions.
    Creates training feedback loop for improving AI model performance.
    """

    submission = models.ForeignKey(
        StudySubmission,
        on_delete=models.CASCADE,
        related_name='ai_corrections',
        help_text=_('Linked study submission')
    )

    domain = models.CharField(
        max_length=2,
        help_text=_('SEND domain code')
    )

    variable = models.CharField(
        max_length=8,
        help_text=_('SEND variable name')
    )

    original_extraction = models.TextField(
        help_text=_('Original AI-extracted value')
    )

    corrected_value = models.TextField(
        help_text=_('Human-corrected value')
    )

    correction_reason = models.TextField(
        help_text=_('Reason for correction and guidance for AI')
    )

    corrected_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='corrections_made',
        help_text=_('User who made the correction')
    )

    correction_type = models.CharField(
        max_length=50,
        help_text=_('Type of correction (e.g., format, value, unit, missing data)')
    )

    added_to_training = models.BooleanField(
        default=False,
        help_text=_('Whether correction has been exported to training dataset')
    )

    training_export_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Date correction was exported for training')
    )

    ai_confidence_before = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('AI confidence score before correction')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('AI Correction')
        verbose_name_plural = _('AI Corrections')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'variable']),
            models.Index(fields=['added_to_training']),
            models.Index(fields=['correction_type']),
        ]

    def __str__(self):
        return f"{self.domain}.{self.variable}: '{self.original_extraction}' → '{self.corrected_value}'"

    def mark_as_training_data(self):
        """Mark correction as added to training dataset"""
        self.added_to_training = True
        self.training_export_date = datetime.now()
        self.save()


class DataProvenance(models.Model):
    """
    Model for tracking data traceability - links every extracted data point
    back to its source location in the original PDF document.
    Ensures FDA regulatory compliance through complete audit trail.
    """

    class ExtractionMethod(models.TextChoices):
        AI = 'AI', _('AI Extraction')
        MANUAL = 'MANUAL', _('Manual Entry')
        CORRECTED = 'CORRECTED', _('AI + Human Correction')

    submission = models.ForeignKey(
        StudySubmission,
        on_delete=models.CASCADE,
        related_name='provenance_records',
        help_text=_('Linked study submission')
    )

    domain = models.CharField(
        max_length=2,
        help_text=_('SEND domain code')
    )

    variable = models.CharField(
        max_length=8,
        help_text=_('SEND variable name')
    )

    value = models.TextField(
        help_text=_('Extracted data value')
    )

    # PDF source information
    pdf_page = models.IntegerField(
        help_text=_('PDF page number where data was found')
    )

    pdf_table = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_('Table identifier or caption')
    )

    pdf_row = models.IntegerField(
        null=True,
        blank=True,
        help_text=_('Row number within table')
    )

    pdf_column = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text=_('Column identifier or header')
    )

    pdf_coordinates = models.JSONField(
        null=True,
        blank=True,
        help_text=_('Bounding box coordinates in PDF (x, y, width, height)')
    )

    extraction_method = models.CharField(
        max_length=10,
        choices=ExtractionMethod.choices,
        default=ExtractionMethod.AI,
        help_text=_('Method used to extract this data')
    )

    extracted_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extracted_data',
        help_text=_('User who extracted/entered the data')
    )

    extracted_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Timestamp of extraction')
    )

    reviewed_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_provenance',
        help_text=_('User who reviewed this data')
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Timestamp of review')
    )

    source_text = models.TextField(
        blank=True,
        null=True,
        help_text=_('Surrounding text context from PDF')
    )

    confidence_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('AI confidence score if applicable')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Data Provenance')
        verbose_name_plural = _('Data Provenance Records')
        ordering = ['pdf_page', 'pdf_table', 'pdf_row']
        indexes = [
            models.Index(fields=['submission', 'domain']),
            models.Index(fields=['pdf_page']),
            models.Index(fields=['extraction_method']),
        ]

    def __str__(self):
        return f"{self.domain}.{self.variable} from page {self.pdf_page}"

    def get_source_location(self):
        """Return human-readable source location string"""
        location = f"Page {self.pdf_page}"
        if self.pdf_table:
            location += f", Table: {self.pdf_table}"
        if self.pdf_row:
            location += f", Row {self.pdf_row}"
        if self.pdf_column:
            location += f", Column: {self.pdf_column}"
        return location

    def mark_reviewed(self, user):
        """Mark provenance record as reviewed"""
        self.reviewed_by = user
        self.reviewed_at = datetime.now()
        self.save()
