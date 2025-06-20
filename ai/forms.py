from django import forms
from django.core.exceptions import ValidationError
from .models import AIModel, AIConfiguration


class AIModelForm(forms.ModelForm):
    """Simple form for AI Model"""
    
    class Meta:
        model = AIModel
        fields = ['name', 'model_type', 'provider', 'namespace', 'is_available']
        
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'model_type': forms.Select(attrs={'class': 'form-select'}),
            'provider': forms.TextInput(attrs={'class': 'form-control'}),
            'namespace': forms.TextInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError("Model name is required.")
        
        # Check uniqueness
        queryset = AIModel.objects.filter(name=name)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError("A model with this name already exists.")
        
        return name


class AIConfigurationForm(forms.ModelForm):
    """Simple form for AI Configuration"""
    
    class Meta:
        model = AIConfiguration
        fields = ['detect_with_ai', 'extract_with_ai', 'use_smart_cache']
        
        widgets = {
            'detect_with_ai': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extract_with_ai': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'use_smart_cache': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }