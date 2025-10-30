"""
Forms for the extractor app and workflow system
"""

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import (
    Study, DocumentUpload, StudySubmission, ReviewComment,
    AICorrection, ExtractedField, User
)


class StudyUploadForm(forms.ModelForm):
    """Form for uploading a new study"""
    
    class Meta:
        model = Study
        fields = ['study_number', 'title', 'description', 'study_sponsor', 'study_type', 'species', 'study_file', 'start_date']
        widgets = {
            'study_number': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Enter unique study identifier'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Enter study title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional study description'
            }),
            'study_sponsor': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Study sponsor'
            }),
            'study_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Toxicology, Safety'
            }),
            'species': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[
                ('', 'Select species'),
                ('RAT', 'Rat'),
                ('MOUSE', 'Mouse'),
                ('DOG', 'Dog'),
                ('MONKEY', 'Non-human primate'),
                ('RABBIT', 'Rabbit'),
                ('PIG', 'Pig'),
                ('OTHER', 'Other'),
            ]),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
                'placeholder': 'Start date (YYYY-MM-DD)'
            }),
            'study_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            }),
        }
    
    def clean_pdf_file(self):
        pdf_file = self.cleaned_data.get('pdf_file')
        if pdf_file:
            if not pdf_file.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed.")
            
            # Check file size (50MB limit)
            if pdf_file.size > 50 * 1024 * 1024:
                raise forms.ValidationError("File size cannot exceed 50MB.")
        
        return pdf_file


# class DomainSelectionForm(forms.Form):
#     """Form for selecting SEND domains to extract"""
    
#     domains = forms.MultipleChoiceField(
#         choices=settings.SENDIG_DOMAINS,
#         widget=forms.CheckboxSelectMultiple(attrs={
#             'class': 'form-check-input'
#         }),
#         required=True,
#         help_text="Select one or more SEND domains to extract from the study document."
#     )
    
#     def clean_domains(self):
#         domains = self.cleaned_data.get('domains')
#         if not domains:
#             raise forms.ValidationError("Please select at least one domain.")
#         return domains


# class DocumentUploadForm(forms.ModelForm):
#     """Form for uploading additional documents"""
    
#     class Meta:
#         model = DocumentUpload
#         fields = ['file']
#         widgets = {
#             'file': forms.FileInput(attrs={
#                 'class': 'form-control',
#                 'accept': '.pdf,.doc,.docx,.txt'
#             }),
#         }
    
#     def clean_file(self):
#         file = self.cleaned_data.get('file')
#         if file:
#             allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
#             file_extension = '.' + file.name.split('.')[-1].lower()
            
#             if file_extension not in allowed_extensions:
#                 raise forms.ValidationError(
#                     f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
#                 )
            
#             # Check file size
#             if file.size > 100 * 1024 * 1024:  # 100MB
#                 raise forms.ValidationError("File size cannot exceed 100MB.")
        
#         return file


class StudyFilterForm(forms.Form):
    """Form for filtering studies"""
    
    STATUS_CHOICES = [
        ('', 'All Studies'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    SPECIES_CHOICES = [
        ('', 'All Species'),
        ('RAT', 'Rat'),
        ('MOUSE', 'Mouse'),
        ('DOG', 'Dog'),
        ('MONKEY', 'Non-human primate'),
        ('RABBIT', 'Rabbit'),
        ('PIG', 'Pig'),
        ('OTHER', 'Other'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    species = forms.ChoiceField(
        choices=SPECIES_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by study ID or title...'
        })
    )


# ======================================================================
# WORKFLOW FORMS
# ======================================================================


class AssignReviewerForm(forms.ModelForm):
    """Form for assigning reviewers to a submission"""

    class Meta:
        model = StudySubmission
        fields = ['assigned_toxicologist', 'assigned_send_expert', 'assigned_qc_reviewer', 'priority']
        widgets = {
            'assigned_toxicologist': forms.Select(attrs={
                'class': 'form-control',
            }),
            'assigned_send_expert': forms.Select(attrs={
                'class': 'form-control',
            }),
            'assigned_qc_reviewer': forms.Select(attrs={
                'class': 'form-control',
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control',
            }, choices=[
                (1, '1 - Critical'),
                (2, '2 - High'),
                (3, '3 - Normal'),
                (4, '4 - Low'),
                (5, '5 - Very Low'),
            ]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter toxicologists
        self.fields['assigned_toxicologist'].queryset = User.objects.filter(
            role=User.UserRole.TOXICOLOGIST,
            is_active=True
        ).order_by('last_name', 'first_name')
        self.fields['assigned_toxicologist'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.department or 'No dept'})"

        # Filter SEND experts
        self.fields['assigned_send_expert'].queryset = User.objects.filter(
            role=User.UserRole.SEND_EXPERT,
            is_active=True
        ).order_by('last_name', 'first_name')
        self.fields['assigned_send_expert'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.specialization or 'SEND Expert'})"

        # Filter QC reviewers
        self.fields['assigned_qc_reviewer'].queryset = User.objects.filter(
            role=User.UserRole.QC_REVIEWER,
            is_active=True
        ).order_by('last_name', 'first_name')
        self.fields['assigned_qc_reviewer'].label_from_instance = lambda obj: f"{obj.get_full_name()} (QC)"


class ReviewCommentForm(forms.ModelForm):
    """Form for adding review comments"""

    class Meta:
        model = ReviewComment
        fields = ['domain', 'variable', 'comment', 'severity']
        widgets = {
            'domain': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., DM, BW, LB (optional)',
                'maxlength': 2,
            }),
            'variable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., STUDYID, USUBJID (optional)',
                'maxlength': 8,
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter your review comment or feedback...',
                'required': True,
            }),
            'severity': forms.Select(attrs={
                'class': 'form-control',
            }),
        }
        help_texts = {
            'domain': 'Optional: Specify SEND domain code if comment is domain-specific',
            'variable': 'Optional: Specify SEND variable if comment is field-specific',
            'severity': 'Select severity level to indicate urgency',
        }

    def clean(self):
        cleaned_data = super().clean()
        domain = cleaned_data.get('domain')
        variable = cleaned_data.get('variable')

        # If variable is specified, domain must be specified too
        if variable and not domain:
            raise ValidationError({
                'domain': 'Domain is required when specifying a variable.'
            })

        return cleaned_data


class ResolveCommentForm(forms.Form):
    """Form for resolving a review comment"""

    resolution_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe how this issue was resolved...',
            'required': True,
        }),
        label='Resolution Notes',
        help_text='Explain what actions were taken to address this comment'
    )


class WorkflowTransitionForm(forms.Form):
    """Form for transitioning workflow status"""

    new_status = forms.ChoiceField(
        choices=[],  # Will be populated dynamically
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Transition To',
        help_text='Select the next workflow status'
    )

    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional: Provide reason for transition (required for rejection)',
        }),
        label='Reason',
        help_text='Reason for this transition (required when rejecting)'
    )

    def __init__(self, submission, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submission = submission

        # Get valid transitions for current status
        valid_statuses = []
        for status_value, status_label in StudySubmission.Status.choices:
            if submission.can_transition_to(status_value):
                valid_statuses.append((status_value, status_label))

        self.fields['new_status'].choices = valid_statuses

        # Make reason required for rejection
        if not self.is_bound:
            self.fields['reason'].required = False

    def clean(self):
        cleaned_data = super().clean()
        new_status = cleaned_data.get('new_status')
        reason = cleaned_data.get('reason')

        # Validate transition
        if new_status and not self.submission.can_transition_to(new_status):
            raise ValidationError({
                'new_status': f'Invalid transition from {self.submission.get_status_display()} to {StudySubmission.Status(new_status).label}'
            })

        # Require reason for rejection
        if new_status == StudySubmission.Status.REJECTED and not reason:
            raise ValidationError({
                'reason': 'Reason is required when rejecting a submission.'
            })

        return cleaned_data


class CorrectionForm(forms.ModelForm):
    """Form for recording AI corrections"""

    class Meta:
        model = AICorrection
        fields = ['domain', 'variable', 'original_extraction', 'corrected_value',
                  'correction_reason', 'correction_type']
        widgets = {
            'domain': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., DM, BW, LB',
                'maxlength': 2,
                'required': True,
            }),
            'variable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., STUDYID, USUBJID',
                'maxlength': 8,
                'required': True,
            }),
            'original_extraction': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Original AI-extracted value',
                'required': True,
            }),
            'corrected_value': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Corrected value',
                'required': True,
            }),
            'correction_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain why this correction was needed and provide guidance for the AI model...',
                'required': True,
            }),
            'correction_type': forms.Select(attrs={
                'class': 'form-control',
            }, choices=[
                ('', 'Select correction type'),
                ('format', 'Format Error'),
                ('value', 'Incorrect Value'),
                ('unit', 'Unit Error'),
                ('missing', 'Missing Data'),
                ('extra', 'Extra/Spurious Data'),
                ('terminology', 'Controlled Terminology Error'),
                ('relationship', 'Relationship Error'),
                ('other', 'Other'),
            ]),
        }
        help_texts = {
            'correction_reason': 'Provide detailed explanation to help improve the AI model',
            'correction_type': 'Categorize the type of error for analytics',
        }

    def clean(self):
        cleaned_data = super().clean()
        original = cleaned_data.get('original_extraction')
        corrected = cleaned_data.get('corrected_value')

        # Ensure values are different
        if original and corrected and original.strip() == corrected.strip():
            raise ValidationError({
                'corrected_value': 'Corrected value must be different from original extraction.'
            })

        return cleaned_data


class ExtractedFieldReviewForm(forms.ModelForm):
    """Form for reviewing individual extracted fields"""

    class Meta:
        model = ExtractedField
        fields = ['value', 'reviewed']
        widgets = {
            'value': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Edit value if needed',
            }),
            'reviewed': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    create_correction = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='Create correction record',
        help_text='Check this if you modified the value to track it for AI training'
    )

    correction_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Reason for correction (required if creating correction record)',
        }),
        label='Correction Reason',
    )

    correction_type = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Select type'),
            ('format', 'Format Error'),
            ('value', 'Incorrect Value'),
            ('unit', 'Unit Error'),
            ('missing', 'Missing Data'),
            ('terminology', 'Controlled Terminology Error'),
            ('other', 'Other'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Correction Type',
    )

    def clean(self):
        cleaned_data = super().clean()
        create_correction = cleaned_data.get('create_correction')
        correction_reason = cleaned_data.get('correction_reason')
        correction_type = cleaned_data.get('correction_type')

        # If creating correction, require reason and type
        if create_correction:
            if not correction_reason:
                raise ValidationError({
                    'correction_reason': 'Correction reason is required when creating correction record.'
                })
            if not correction_type:
                raise ValidationError({
                    'correction_type': 'Correction type is required when creating correction record.'
                })

        return cleaned_data


class SubmissionFilterForm(forms.Form):
    """Form for filtering workflow submissions"""

    status = forms.MultipleChoiceField(
        choices=StudySubmission.Status.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
        label='Status',
    )

    priority = forms.MultipleChoiceField(
        choices=[
            (1, 'Critical'),
            (2, 'High'),
            (3, 'Normal'),
            (4, 'Low'),
            (5, 'Very Low'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
        label='Priority',
    )

    assigned_to_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='Assigned to me',
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by submission ID or study title...',
        }),
        label='Search',
    )


class BulkApproveForm(forms.Form):
    """Form for bulk approval of submissions"""

    submission_ids = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
        label='Select Submissions',
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes for bulk approval...',
        }),
        label='Notes',
    )

    def __init__(self, queryset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['submission_ids'].choices = [
            (sub.id, f"{sub.submission_id} - {sub.study.title}")
            for sub in queryset
        ]
