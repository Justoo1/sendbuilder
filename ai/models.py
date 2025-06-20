from django.db import models

class AIModel(models.Model):
    """Track available AI models"""
    
    MODEL_TYPES = [
        ('CHAT', 'Chat Model'),
        ('EMBEDDING', 'Embedding Model'),
        ('CODE', 'Code Model'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    model_type = models.CharField(max_length=20, choices=MODEL_TYPES)
    
    # Model configuration
    provider = models.CharField(max_length=50, default='ollama')  # ollama, openai, etc.
    model_size = models.CharField(max_length=50, blank=True, help_text="e.g. 7b, 13b, etc.")  # 7b, 13b, etc.
    context_length = models.IntegerField(default=4096)
    namespace = models.CharField(max_length=50, blank=True, help_text="deepseek-r1, llama-2, etc.")
    
    # Performance metrics
    is_available = models.BooleanField(default=True)
    average_response_time = models.FloatField(null=True, blank=True)
    last_health_check = models.DateTimeField(null=True, blank=True)
    
    # Configuration
    temperature = models.FloatField(default=0.1)
    max_tokens = models.IntegerField(default=2048)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI Model"
        verbose_name_plural = "AI Models"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.model_type})"
    
    def get_absolute_url(self):
        return f'/ai/models/{self.id}/'
    

class AIConfiguration(models.Model):
    """Track AI model configurations"""
    detect_with_ai = models.BooleanField(default=False)
    extract_with_ai = models.BooleanField(default=False)
    use_smart_cache = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "AI Configuration"
        verbose_name_plural = "AI Configurations"

    def __str__(self):
        return "AI Configuration"
    
    def get_absolute_url(self):
        return f'/ai/config/{self.id}/'
