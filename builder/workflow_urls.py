"""
URL Configuration for Workflow System

Maps URLs to workflow views for the multi-layer validation system.
"""

from django.urls import path
from builder import workflow_views

app_name = 'workflow'

urlpatterns = [
    # Dashboard URLs
    path('dashboard/', workflow_views.WorkflowDashboardView.as_view(), name='dashboard'),
    path('admin-dashboard/', workflow_views.AdminDashboardView.as_view(), name='admin_dashboard'),

    # Submission Management URLs
    path('submission/<int:pk>/', workflow_views.SubmissionDetailView.as_view(), name='submission_detail'),
    path('submission/<int:pk>/assign/', workflow_views.AssignReviewersView.as_view(), name='assign_reviewers'),
    path('submission/<int:submission_id>/transition/', workflow_views.transition_workflow_view, name='transition_workflow'),

    # Review Interface URLs
    path('submission/<int:pk>/toxicologist-review/', workflow_views.ToxicologistReviewView.as_view(), name='toxicologist_review'),
    path('submission/<int:pk>/send-expert-review/', workflow_views.SENDExpertReviewView.as_view(), name='send_expert_review'),
    path('submission/<int:pk>/qc-review/', workflow_views.QCReviewView.as_view(), name='qc_review'),

    # Comment Management URLs
    path('submission/<int:submission_id>/add-comment/', workflow_views.add_comment_view, name='add_comment'),
    path('comment/<int:comment_id>/resolve/', workflow_views.resolve_comment_view, name='resolve_comment'),

    # Confidence Analysis URLs
    path('submission/<int:pk>/confidence/', workflow_views.ConfidenceAnalysisView.as_view(), name='confidence_analysis'),

    # Correction Tracking URLs
    path('submission/<int:submission_id>/add-correction/', workflow_views.add_correction_view, name='add_correction'),
    path('analytics/corrections/', workflow_views.CorrectionAnalyticsView.as_view(), name='correction_analytics'),
    path('analytics/export-training-data/', workflow_views.export_training_data_view, name='export_training_data'),

    # Traceability URLs
    path('submission/<int:pk>/traceability/', workflow_views.TraceabilityReportView.as_view(), name='traceability_report'),
    path('submission/<int:submission_id>/traceability/export/', workflow_views.export_traceability_csv, name='export_traceability'),

    # API Endpoints (AJAX)
    path('api/submission/<int:submission_id>/status/', workflow_views.submission_status_api, name='submission_status_api'),
    path('api/submission/<int:submission_id>/confidence/', workflow_views.confidence_summary_api, name='confidence_summary_api'),
]
