"""
Forms for the extractor app
"""

from django import forms
from django.conf import settings
from .models import Study, DocumentUpload


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
