from django.urls import path
from . import views

app_name = 'builder'

urlpatterns = [
    path('', views.home, name='dashboard'),
    path('upload/', views.StudyUploadView.as_view(), name='upload_study'),

    # Domain detection
    path('detect-domain/<int:pk>/', views.detect_domain, name='detect_domain'),
    path('study/<int:pk>/detect/status/', views.detection_status, name='detection_status'),
    path('study/<int:pk>/detect/rerun/', views.redetect_domains, name='redetect_domains'),
    path('study/<int:pk>/detect/results/', views.detection_results, name='detection_results'),
    path('study/<int:pk>/detect/<int:detection_id>/', views.detection_detail, name='detection_detail'),
    
    # Domain extraction
    path('extraction/<int:study_id>/', views.ExtractionDashboardView.as_view(), name='dashboard'),
    path('extraction/<int:study_id>/extract/', views.StartExtractionView.as_view(), name='start_extraction'),
    path('extraction/<int:study_id>/extract-all/', views.ExtractAllDomainsView.as_view(), name='extract_all'),
    path('extraction/<int:study_id>/status/<str:domain_code>/', views.ExtractionStatusView.as_view(), name='extraction_status'),
    path('extraction/<int:study_id>/generate-fda/', views.GenerateFDAFilesView.as_view(), name='generate_fda'),
    path('extraction/<int:study_id>/results/', views.ResultsView.as_view(), name='results'),
    path('extraction/<int:study_id>/download/<str:file_type>/', views.DownloadFileView.as_view(), name='download_file'),
    path('extraction/<int:study_id>/download/<str:file_type>/<str:domain_code>/', views.DownloadFileView.as_view(), name='download_domain_file'),

    # API endpoints
    # path('api/study/<int:study_id>/detect/', views.api_detect_domains, name='api_detect_domains'),
    # path('api/study/<int:study_id>/detect/status/', views.api_detection_status, name='api_detection_status'),
    
    # Webhook for external integrations
    # path('webhook/detect/', views.detection_webhook, name='detection_webhook'),
]