from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    # AI Models
    path('models/', views.aimodel_list, name='aimodel_list'),
    path('models/create/', views.aimodel_create, name='aimodel_create'),
    path('models/<int:pk>/edit/', views.aimodel_update, name='aimodel_update'),
    path('models/<int:pk>/delete/', views.aimodel_delete, name='aimodel_delete'),
    
    # AI Configuration
    path('config/', views.ai_configuration, name='ai_configuration'),
]