"""
Workflow Views for Multi-Layer Validation System

This module contains all views for the workflow system including:
- Role-based dashboards
- Review interfaces for each role
- Confidence scoring views
- Traceability reports
- AI correction tracking
- Analytics dashboards
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Avg
from datetime import datetime
import csv
import json

from builder.models import (
    User, StudySubmission, ExtractedField, ReviewComment,
    AICorrection, DataProvenance, Study
)
from builder.forms import (
    AssignReviewerForm, ReviewCommentForm, ResolveCommentForm,
    WorkflowTransitionForm, CorrectionForm, ExtractedFieldReviewForm,
    SubmissionFilterForm
)
from builder.decorators import (
    role_required, can_review_submission, RoleRequiredMixin,
    CanReviewSubmissionMixin, SubmissionContextMixin, ReviewerDashboardMixin
)
from builder.utils.workflow_services import (
    WorkflowService, ConfidenceAnalysisService,
    TraceabilityService, CorrectionAnalyticsService
)


# ======================================================================
# DASHBOARD VIEWS
# ======================================================================


class WorkflowDashboardView(ReviewerDashboardMixin, TemplateView):
    """
    Main workflow dashboard showing pending reviews based on user role.
    """
    template_name = 'workflow/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add filter form
        filter_form = SubmissionFilterForm(self.request.GET or None)
        context['filter_form'] = filter_form

        # Apply filters if submitted
        if filter_form.is_valid():
            queryset = context['pending_submissions']

            if filter_form.cleaned_data.get('status'):
                queryset = queryset.filter(status__in=filter_form.cleaned_data['status'])

            if filter_form.cleaned_data.get('priority'):
                queryset = queryset.filter(priority__in=filter_form.cleaned_data['priority'])

            if filter_form.cleaned_data.get('search'):
                search_term = filter_form.cleaned_data['search']
                queryset = queryset.filter(
                    Q(submission_id__icontains=search_term) |
                    Q(study__title__icontains=search_term) |
                    Q(study__study_number__icontains=search_term)
                )

            context['pending_submissions'] = queryset

        return context


class AdminDashboardView(RoleRequiredMixin, TemplateView):
    """
    Administrator dashboard with system-wide statistics and controls.
    """
    template_name = 'workflow/admin_dashboard.html'
    required_roles = [User.UserRole.ADMIN]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all submissions grouped by status
        submissions = StudySubmission.objects.all()
        context['total_submissions'] = submissions.count()

        # Status breakdown
        status_counts = {}
        for status_value, status_label in StudySubmission.Status.choices:
            count = submissions.filter(status=status_value).count()
            status_counts[status_label] = count
        context['status_counts'] = status_counts

        # Recent submissions
        context['recent_submissions'] = submissions.select_related(
            'study', 'assigned_toxicologist', 'assigned_send_expert', 'assigned_qc_reviewer'
        ).order_by('-created_at')[:10]

        # Reviewer workload
        context['toxicologists'] = User.objects.filter(
            role=User.UserRole.TOXICOLOGIST,
            is_active=True
        ).annotate(
            pending_count=Count('tox_reviews', filter=Q(tox_reviews__status=StudySubmission.Status.TOXICOLOGIST_REVIEW))
        )

        context['send_experts'] = User.objects.filter(
            role=User.UserRole.SEND_EXPERT,
            is_active=True
        ).annotate(
            pending_count=Count('send_reviews', filter=Q(send_reviews__status=StudySubmission.Status.SEND_EXPERT_REVIEW))
        )

        context['qc_reviewers'] = User.objects.filter(
            role=User.UserRole.QC_REVIEWER,
            is_active=True
        ).annotate(
            pending_count=Count('qc_reviews', filter=Q(qc_reviews__status=StudySubmission.Status.QC_REVIEW))
        )

        # System statistics
        context['total_corrections'] = AICorrection.objects.count()
        context['total_comments'] = ReviewComment.objects.count()
        context['unresolved_critical'] = ReviewComment.objects.filter(
            severity=ReviewComment.Severity.CRITICAL,
            resolved=False
        ).count()

        return context


# ======================================================================
# SUBMISSION MANAGEMENT VIEWS
# ======================================================================


class SubmissionDetailView(CanReviewSubmissionMixin, SubmissionContextMixin, DetailView):
    """
    Detailed view of a submission with all extracted data and comments.
    """
    model = StudySubmission
    template_name = 'workflow/submission_detail.html'
    context_object_name = 'submission'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = self.object

        # Get extracted fields
        context['extracted_fields'] = ExtractedField.objects.filter(
            submission=submission
        ).order_by('domain', 'variable')

        # Get comments
        context['comments'] = ReviewComment.objects.filter(
            submission=submission
        ).select_related('reviewer', 'resolved_by').order_by('-created_at')

        # Get corrections
        context['corrections'] = AICorrection.objects.filter(
            submission=submission
        ).select_related('corrected_by').order_by('-created_at')

        # Get confidence summary
        context['confidence_summary'] = ConfidenceAnalysisService.get_confidence_summary(submission)

        # Get workflow transition form
        context['transition_form'] = WorkflowTransitionForm(submission)

        return context


class AssignReviewersView(RoleRequiredMixin, UpdateView):
    """
    View for assigning reviewers to a submission.
    """
    model = StudySubmission
    form_class = AssignReviewerForm
    template_name = 'workflow/assign_reviewers.html'
    required_roles = [User.UserRole.ADMIN]

    def get_success_url(self):
        return reverse('workflow:submission_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Reviewers assigned successfully.')

        # Send notifications
        submission = self.object
        if submission.assigned_toxicologist:
            WorkflowService.send_assignment_notification(
                submission, submission.assigned_toxicologist, 'toxicologist'
            )
        if submission.assigned_send_expert:
            WorkflowService.send_assignment_notification(
                submission, submission.assigned_send_expert, 'send_expert'
            )
        if submission.assigned_qc_reviewer:
            WorkflowService.send_assignment_notification(
                submission, submission.assigned_qc_reviewer, 'qc_reviewer'
            )

        return response


@login_required
@can_review_submission
def transition_workflow_view(request, submission_id):
    """
    Handle workflow status transitions.
    """
    submission = get_object_or_404(StudySubmission, pk=submission_id)

    if request.method == 'POST':
        form = WorkflowTransitionForm(submission, request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['new_status']
            reason = form.cleaned_data.get('reason')

            result = WorkflowService.transition_workflow(
                submission=submission,
                new_status=new_status,
                user=request.user,
                reason=reason
            )

            if result['success']:
                messages.success(request, result['message'])
            else:
                messages.error(request, result['message'])

            return redirect('workflow:submission_detail', pk=submission_id)
    else:
        form = WorkflowTransitionForm(submission)

    return render(request, 'workflow/transition.html', {
        'form': form,
        'submission': submission,
    })


# ======================================================================
# REVIEW INTERFACE VIEWS
# ======================================================================


class ToxicologistReviewView(CanReviewSubmissionMixin, SubmissionContextMixin, DetailView):
    """
    Toxicologist review interface for scientific validation.
    """
    model = StudySubmission
    template_name = 'workflow/toxicologist_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = self.object

        # Get low confidence fields for review
        context['low_confidence_fields'] = ConfidenceAnalysisService.get_fields_by_confidence(
            submission, level='low'
        )

        # Get medium confidence fields
        context['medium_confidence_fields'] = ConfidenceAnalysisService.get_fields_by_confidence(
            submission, level='medium'
        )

        # Get high confidence fields
        context['high_confidence_fields'] = ConfidenceAnalysisService.get_fields_by_confidence(
            submission, level='high'
        )

        # Get domain-specific confidence
        context['domain_confidence'] = ConfidenceAnalysisService.get_domain_confidence_summary(submission)

        # Forms
        context['comment_form'] = ReviewCommentForm()
        context['correction_form'] = CorrectionForm()

        return context


class SENDExpertReviewView(CanReviewSubmissionMixin, SubmissionContextMixin, DetailView):
    """
    SEND Expert review interface for compliance validation.
    """
    model = StudySubmission
    template_name = 'workflow/send_expert_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = self.object

        # Get fields requiring review
        context['fields_requiring_review'] = ExtractedField.objects.filter(
            submission=submission,
            requires_review=True
        ).order_by('domain', 'variable')

        # Get previous comments
        context['previous_comments'] = ReviewComment.objects.filter(
            submission=submission
        ).select_related('reviewer').order_by('-created_at')

        # Get traceability report
        context['traceability'] = TraceabilityService.get_traceability_report(submission)

        # Forms
        context['comment_form'] = ReviewCommentForm()

        return context


class QCReviewView(CanReviewSubmissionMixin, SubmissionContextMixin, DetailView):
    """
    QC Reviewer interface for final quality check.
    """
    model = StudySubmission
    template_name = 'workflow/qc_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = self.object

        # Get all comments
        context['all_comments'] = ReviewComment.objects.filter(
            submission=submission
        ).select_related('reviewer', 'resolved_by').order_by('severity', 'resolved', '-created_at')

        # Get unresolved critical issues
        context['unresolved_critical'] = context['all_comments'].filter(
            severity=ReviewComment.Severity.CRITICAL,
            resolved=False
        )

        # Get all corrections
        context['all_corrections'] = AICorrection.objects.filter(
            submission=submission
        ).select_related('corrected_by').order_by('-created_at')

        # Get confidence summary
        context['confidence_summary'] = ConfidenceAnalysisService.get_confidence_summary(submission)

        # Check if ready for approval
        context['ready_for_approval'] = (
            context['unresolved_critical'].count() == 0 and
            context['confidence_summary']['requires_review'] == 0
        )

        # Forms
        context['comment_form'] = ReviewCommentForm()

        return context


# ======================================================================
# COMMENT MANAGEMENT VIEWS
# ======================================================================


@login_required
@can_review_submission
def add_comment_view(request, submission_id):
    """
    Add a review comment to a submission.
    """
    submission = get_object_or_404(StudySubmission, pk=submission_id)

    if request.method == 'POST':
        form = ReviewCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.submission = submission
            comment.reviewer = request.user
            comment.save()

            messages.success(request, 'Comment added successfully.')

            # If AJAX request, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Comment added successfully.'
                })

            return redirect('workflow:submission_detail', pk=submission_id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)

    return redirect('workflow:submission_detail', pk=submission_id)


@login_required
def resolve_comment_view(request, comment_id):
    """
    Resolve a review comment.
    """
    comment = get_object_or_404(ReviewComment, pk=comment_id)

    # Check permission
    if not request.user.can_review_submission(comment.submission):
        messages.error(request, 'You do not have permission to resolve this comment.')
        return redirect('workflow:submission_detail', pk=comment.submission.pk)

    if request.method == 'POST':
        form = ResolveCommentForm(request.POST)
        if form.is_valid():
            resolution_notes = form.cleaned_data['resolution_notes']
            comment.resolve(user=request.user, notes=resolution_notes)

            messages.success(request, 'Comment resolved successfully.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Comment resolved successfully.'
                })

            return redirect('workflow:submission_detail', pk=comment.submission.pk)

    return redirect('workflow:submission_detail', pk=comment.submission.pk)


# ======================================================================
# CONFIDENCE SCORING VIEWS
# ======================================================================


class ConfidenceAnalysisView(CanReviewSubmissionMixin, SubmissionContextMixin, DetailView):
    """
    Detailed confidence score analysis view.
    """
    model = StudySubmission
    template_name = 'workflow/confidence_analysis.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = self.object

        # Get comprehensive confidence summary
        context['confidence_summary'] = ConfidenceAnalysisService.get_confidence_summary(submission)

        # Get domain-specific confidence
        context['domain_confidence'] = ConfidenceAnalysisService.get_domain_confidence_summary(submission)

        # Get fields grouped by confidence level
        context['high_conf_fields'] = ConfidenceAnalysisService.get_fields_by_confidence(
            submission, level='high'
        )[:50]  # Limit to 50

        context['medium_conf_fields'] = ConfidenceAnalysisService.get_fields_by_confidence(
            submission, level='medium'
        )[:50]

        context['low_conf_fields'] = ConfidenceAnalysisService.get_fields_by_confidence(
            submission, level='low'
        )

        return context


# ======================================================================
# CORRECTION TRACKING VIEWS
# ======================================================================


@login_required
@can_review_submission
def add_correction_view(request, submission_id):
    """
    Add an AI correction record.
    """
    submission = get_object_or_404(StudySubmission, pk=submission_id)

    if request.method == 'POST':
        form = CorrectionForm(request.POST)
        if form.is_valid():
            correction = form.save(commit=False)
            correction.submission = submission
            correction.corrected_by = request.user
            correction.save()

            messages.success(request, 'Correction recorded successfully.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Correction recorded successfully.'
                })

            return redirect('workflow:submission_detail', pk=submission_id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)

    return redirect('workflow:submission_detail', pk=submission_id)


class CorrectionAnalyticsView(RoleRequiredMixin, TemplateView):
    """
    Analytics dashboard for AI corrections.
    """
    template_name = 'workflow/correction_analytics.html'
    required_roles = [User.UserRole.ADMIN, User.UserRole.SEND_EXPERT]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get overall correction patterns
        context['patterns'] = CorrectionAnalyticsService.get_correction_patterns()

        # Get domain-specific patterns
        domain_filter = self.request.GET.get('domain')
        if domain_filter:
            context['domain_patterns'] = CorrectionAnalyticsService.get_correction_patterns(
                domain=domain_filter
            )
            context['selected_domain'] = domain_filter

        # Get recent corrections
        context['recent_corrections'] = AICorrection.objects.select_related(
            'submission', 'corrected_by'
        ).order_by('-created_at')[:20]

        return context


@login_required
@role_required(User.UserRole.ADMIN)
def export_training_data_view(request):
    """
    Export corrections as training dataset.
    """
    output_format = request.GET.get('format', 'csv')

    try:
        filepath = CorrectionAnalyticsService.export_training_dataset(output_format)

        with open(filepath, 'rb') as f:
            content = f.read()

        content_type = 'text/csv' if output_format == 'csv' else 'application/json'
        filename = filepath.split('/')[-1]

        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        messages.success(request, f'Training dataset exported successfully as {output_format.upper()}.')

        return response

    except Exception as e:
        messages.error(request, f'Error exporting training data: {str(e)}')
        return redirect('workflow:correction_analytics')


# ======================================================================
# TRACEABILITY VIEWS
# ======================================================================


class TraceabilityReportView(CanReviewSubmissionMixin, SubmissionContextMixin, DetailView):
    """
    Comprehensive traceability report linking data to PDF sources.
    """
    model = StudySubmission
    template_name = 'workflow/traceability_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = self.object

        # Get full traceability report
        context['traceability_report'] = TraceabilityService.get_traceability_report(submission)

        # Get provenance records grouped by domain
        context['provenance_by_domain'] = {}
        provenance_records = DataProvenance.objects.filter(
            submission=submission
        ).select_related('extracted_by', 'reviewed_by').order_by('pdf_page', 'domain')

        for record in provenance_records:
            if record.domain not in context['provenance_by_domain']:
                context['provenance_by_domain'][record.domain] = []
            context['provenance_by_domain'][record.domain].append(record)

        return context


@login_required
@can_review_submission
def export_traceability_csv(request, submission_id):
    """
    Export traceability report as CSV.
    """
    submission = get_object_or_404(StudySubmission, pk=submission_id)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="traceability_{submission.submission_id}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Domain', 'Variable', 'Value', 'PDF Page', 'PDF Table', 'PDF Row', 'PDF Column',
        'Extraction Method', 'Confidence Score', 'Extracted By', 'Extracted At'
    ])

    provenance_records = DataProvenance.objects.filter(
        submission=submission
    ).select_related('extracted_by').order_by('pdf_page', 'domain', 'variable')

    for record in provenance_records:
        writer.writerow([
            record.domain,
            record.variable,
            record.value,
            record.pdf_page,
            record.pdf_table or '',
            record.pdf_row or '',
            record.pdf_column or '',
            record.get_extraction_method_display(),
            record.confidence_score or '',
            record.extracted_by.get_full_name() if record.extracted_by else '',
            record.extracted_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response


# ======================================================================
# API ENDPOINTS (AJAX)
# ======================================================================


@login_required
def submission_status_api(request, submission_id):
    """
    API endpoint to get current submission status (for polling).
    """
    submission = get_object_or_404(StudySubmission, pk=submission_id)

    return JsonResponse({
        'status': submission.status,
        'status_display': submission.get_status_display(),
        'updated_at': submission.updated_at.isoformat(),
    })


@login_required
def confidence_summary_api(request, submission_id):
    """
    API endpoint to get confidence summary (for dynamic updates).
    """
    submission = get_object_or_404(StudySubmission, pk=submission_id)
    summary = ConfidenceAnalysisService.get_confidence_summary(submission)

    return JsonResponse(summary)
