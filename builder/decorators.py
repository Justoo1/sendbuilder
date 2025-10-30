"""
Permission decorators and mixins for workflow access control.

These decorators enforce role-based permissions for views and methods.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseForbidden

from builder.models import User, StudySubmission


def role_required(*roles):
    """
    Decorator to require specific user roles.

    Usage:
        @role_required('ADMIN', 'TOXICOLOGIST')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not hasattr(request.user, 'role'):
                raise PermissionDenied("User does not have a role assigned.")

            if request.user.role not in roles:
                raise PermissionDenied(
                    f"This view requires one of the following roles: {', '.join(roles)}"
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """
    Decorator to require ADMIN role.

    Usage:
        @admin_required
        def my_view(request):
            ...
    """
    return role_required(User.UserRole.ADMIN)(view_func)


def toxicologist_required(view_func):
    """
    Decorator to require TOXICOLOGIST role.

    Usage:
        @toxicologist_required
        def my_view(request):
            ...
    """
    return role_required(User.UserRole.TOXICOLOGIST)(view_func)


def send_expert_required(view_func):
    """
    Decorator to require SEND_EXPERT role.

    Usage:
        @send_expert_required
        def my_view(request):
            ...
    """
    return role_required(User.UserRole.SEND_EXPERT)(view_func)


def qc_reviewer_required(view_func):
    """
    Decorator to require QC_REVIEWER role.

    Usage:
        @qc_reviewer_required
        def my_view(request):
            ...
    """
    return role_required(User.UserRole.QC_REVIEWER)(view_func)


def can_review_submission(view_func):
    """
    Decorator to check if user can review a specific submission.
    Expects 'submission_id' in URL kwargs.

    Usage:
        @can_review_submission
        def review_view(request, submission_id):
            ...
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        submission_id = kwargs.get('submission_id') or kwargs.get('pk')
        if not submission_id:
            raise PermissionDenied("Submission ID not provided.")

        submission = get_object_or_404(StudySubmission, pk=submission_id)

        # Check if user can review
        if not request.user.can_review_submission(submission):
            raise PermissionDenied(
                "You do not have permission to review this submission."
            )

        return view_func(request, *args, **kwargs)
    return wrapper


def submission_status_required(*statuses):
    """
    Decorator to require submission to be in specific status(es).
    Expects 'submission_id' or 'pk' in URL kwargs.

    Usage:
        @submission_status_required('TOXICOLOGIST_REVIEW', 'SEND_EXPERT_REVIEW')
        def my_view(request, submission_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            submission_id = kwargs.get('submission_id') or kwargs.get('pk')
            if not submission_id:
                raise PermissionDenied("Submission ID not provided.")

            submission = get_object_or_404(StudySubmission, pk=submission_id)

            if submission.status not in statuses:
                raise PermissionDenied(
                    f"Submission must be in one of these statuses: {', '.join(statuses)}"
                )

            # Add submission to kwargs for convenience
            kwargs['submission'] = submission

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ======================================================================
# CLASS-BASED VIEW MIXINS
# ======================================================================


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin to require specific user roles for class-based views.

    Usage:
        class MyView(RoleRequiredMixin, View):
            required_roles = ['ADMIN', 'TOXICOLOGIST']
    """
    required_roles = []

    def test_func(self):
        if not self.required_roles:
            return True

        if not hasattr(self.request.user, 'role'):
            return False

        return self.request.user.role in self.required_roles

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()

        return HttpResponseForbidden(
            f"This view requires one of the following roles: {', '.join(self.required_roles)}"
        )


class AdminRequiredMixin(RoleRequiredMixin):
    """Mixin to require ADMIN role"""
    required_roles = [User.UserRole.ADMIN]


class ToxicologistRequiredMixin(RoleRequiredMixin):
    """Mixin to require TOXICOLOGIST role"""
    required_roles = [User.UserRole.TOXICOLOGIST]


class SENDExpertRequiredMixin(RoleRequiredMixin):
    """Mixin to require SEND_EXPERT role"""
    required_roles = [User.UserRole.SEND_EXPERT]


class QCReviewerRequiredMixin(RoleRequiredMixin):
    """Mixin to require QC_REVIEWER role"""
    required_roles = [User.UserRole.QC_REVIEWER]


class CanReviewSubmissionMixin(LoginRequiredMixin):
    """
    Mixin to check if user can review a specific submission.
    Expects 'pk' or 'submission_id' in URL kwargs.

    Usage:
        class MyView(CanReviewSubmissionMixin, DetailView):
            model = StudySubmission
    """

    def dispatch(self, request, *args, **kwargs):
        submission_id = kwargs.get('pk') or kwargs.get('submission_id')
        if not submission_id:
            return HttpResponseForbidden("Submission ID not provided.")

        submission = get_object_or_404(StudySubmission, pk=submission_id)

        if not request.user.can_review_submission(submission):
            return HttpResponseForbidden(
                "You do not have permission to review this submission."
            )

        # Store submission for use in view
        self.submission = submission

        return super().dispatch(request, *args, **kwargs)


class SubmissionContextMixin:
    """
    Mixin to add submission and related context to template.

    Usage:
        class MyView(SubmissionContextMixin, DetailView):
            model = StudySubmission
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if hasattr(self, 'submission'):
            submission = self.submission
        elif hasattr(self, 'object') and isinstance(self.object, StudySubmission):
            submission = self.object
        else:
            # Try to get from URL kwargs
            submission_id = self.kwargs.get('pk') or self.kwargs.get('submission_id')
            if submission_id:
                submission = get_object_or_404(StudySubmission, pk=submission_id)
            else:
                return context

        # Add submission context
        context['submission'] = submission
        context['study'] = submission.study
        context['workflow_status'] = submission.get_status_display()
        context['can_review'] = self.request.user.can_review_submission(submission)

        # Add valid transitions
        valid_transitions = []
        for status_value, status_label in StudySubmission.Status.choices:
            if submission.can_transition_to(status_value):
                valid_transitions.append({
                    'value': status_value,
                    'label': status_label
                })
        context['valid_transitions'] = valid_transitions

        # Add role information
        context['is_admin'] = self.request.user.role == User.UserRole.ADMIN
        context['is_toxicologist'] = self.request.user.role == User.UserRole.TOXICOLOGIST
        context['is_send_expert'] = self.request.user.role == User.UserRole.SEND_EXPERT
        context['is_qc_reviewer'] = self.request.user.role == User.UserRole.QC_REVIEWER

        return context


class ReviewerDashboardMixin:
    """
    Mixin to add reviewer-specific dashboard context.

    Usage:
        class DashboardView(ReviewerDashboardMixin, TemplateView):
            template_name = 'workflow/dashboard.html'
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get pending reviews based on role
        if user.role == User.UserRole.TOXICOLOGIST:
            pending = StudySubmission.objects.filter(
                assigned_toxicologist=user,
                status=StudySubmission.Status.TOXICOLOGIST_REVIEW
            )
            context['role_name'] = 'Toxicologist'
            context['review_type'] = 'Scientific Review'

        elif user.role == User.UserRole.SEND_EXPERT:
            pending = StudySubmission.objects.filter(
                assigned_send_expert=user,
                status=StudySubmission.Status.SEND_EXPERT_REVIEW
            )
            context['role_name'] = 'SEND Expert'
            context['review_type'] = 'SEND Compliance Review'

        elif user.role == User.UserRole.QC_REVIEWER:
            pending = StudySubmission.objects.filter(
                assigned_qc_reviewer=user,
                status=StudySubmission.Status.QC_REVIEW
            )
            context['role_name'] = 'QC Reviewer'
            context['review_type'] = 'Quality Control Review'

        elif user.role == User.UserRole.ADMIN:
            pending = StudySubmission.objects.all()
            context['role_name'] = 'Administrator'
            context['review_type'] = 'All Submissions'

        else:
            pending = StudySubmission.objects.none()
            context['role_name'] = 'User'
            context['review_type'] = 'No Reviews'

        context['pending_submissions'] = pending.select_related('study').order_by('-priority', 'created_at')
        context['pending_count'] = pending.count()

        # Get reviewer statistics
        from builder.utils.workflow_services import WorkflowService
        context['statistics'] = WorkflowService.get_reviewer_statistics(user)

        return context
