from django.db import models
from django.contrib.auth.models import User

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
    study_file = models.FileField(upload_to='study_files/', blank=True, null=True)
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

class DocumentUpload(models.Model):
    """Model to track uploaded documents"""
    file = models.FileField(upload_to='uploads/')
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
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
    xpt_file = models.FileField(upload_to='xpt_files/', blank=True, null=True)
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
    