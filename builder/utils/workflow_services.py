"""
Workflow Service Functions for SEND Builder

This module provides utility functions for managing the multi-layer validation workflow,
including reviewer assignments, email notifications, and workflow transitions.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from django.db.models import Q, Count, Avg
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from builder.models import (
    User, StudySubmission, ExtractedField, ReviewComment,
    AICorrection, DataProvenance
)


class WorkflowService:
    """Service class for managing workflow operations"""

    @staticmethod
    def assign_reviewers(submission: StudySubmission, auto_assign: bool = True) -> Dict[str, Any]:
        """
        Assign reviewers to a submission based on availability and workload.

        Args:
            submission: StudySubmission instance
            auto_assign: If True, automatically assign based on workload

        Returns:
            Dict with assignment results
        """
        result = {
            'toxicologist': None,
            'send_expert': None,
            'qc_reviewer': None,
            'errors': []
        }

        if not auto_assign:
            return result

        # Find available toxicologist with lowest workload
        toxicologist = User.objects.filter(
            role=User.UserRole.TOXICOLOGIST,
            is_available=True,
            is_active=True
        ).annotate(
            pending_count=Count('tox_reviews', filter=Q(
                tox_reviews__status=StudySubmission.Status.TOXICOLOGIST_REVIEW
            ))
        ).order_by('pending_count').first()

        if toxicologist:
            submission.assigned_toxicologist = toxicologist
            result['toxicologist'] = toxicologist
        else:
            result['errors'].append('No available toxicologist found')

        # Find available SEND expert
        send_expert = User.objects.filter(
            role=User.UserRole.SEND_EXPERT,
            is_available=True,
            is_active=True
        ).annotate(
            pending_count=Count('send_reviews', filter=Q(
                send_reviews__status=StudySubmission.Status.SEND_EXPERT_REVIEW
            ))
        ).order_by('pending_count').first()

        if send_expert:
            submission.assigned_send_expert = send_expert
            result['send_expert'] = send_expert
        else:
            result['errors'].append('No available SEND expert found')

        # Find available QC reviewer
        qc_reviewer = User.objects.filter(
            role=User.UserRole.QC_REVIEWER,
            is_available=True,
            is_active=True
        ).annotate(
            pending_count=Count('qc_reviews', filter=Q(
                qc_reviews__status=StudySubmission.Status.QC_REVIEW
            ))
        ).order_by('pending_count').first()

        if qc_reviewer:
            submission.assigned_qc_reviewer = qc_reviewer
            result['qc_reviewer'] = qc_reviewer
        else:
            result['errors'].append('No available QC reviewer found')

        submission.save()
        return result

    @staticmethod
    def send_assignment_notification(submission: StudySubmission, reviewer: User, role: str):
        """
        Send email notification to reviewer about new assignment.

        Args:
            submission: StudySubmission instance
            reviewer: User assigned as reviewer
            role: Role type (toxicologist, send_expert, qc_reviewer)
        """
        subject = f'New Assignment: {submission.submission_id}'

        context = {
            'reviewer': reviewer,
            'submission': submission,
            'study': submission.study,
            'role': role,
            'dashboard_url': f'/workflow/dashboard/',  # Update with actual URL
        }

        html_message = render_to_string('emails/reviewer_assignment.html', context)
        plain_message = strip_tags(html_message)

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reviewer.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send email to {reviewer.email}: {e}")

    @staticmethod
    def transition_workflow(
        submission: StudySubmission,
        new_status: str,
        user: User,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transition submission to new workflow status with validation.

        Args:
            submission: StudySubmission instance
            new_status: Target status
            user: User performing the transition
            reason: Optional reason (required for rejection)

        Returns:
            Dict with success status and message
        """
        try:
            # Validate transition
            if not submission.can_transition_to(new_status):
                return {
                    'success': False,
                    'message': f'Invalid transition from {submission.get_status_display()} to {new_status}'
                }

            # Perform transition
            submission.transition_to(new_status, user=user, reason=reason)

            # Send notifications if needed
            if new_status == StudySubmission.Status.TOXICOLOGIST_REVIEW and submission.assigned_toxicologist:
                WorkflowService.send_assignment_notification(
                    submission, submission.assigned_toxicologist, 'toxicologist'
                )
            elif new_status == StudySubmission.Status.SEND_EXPERT_REVIEW and submission.assigned_send_expert:
                WorkflowService.send_assignment_notification(
                    submission, submission.assigned_send_expert, 'send_expert'
                )
            elif new_status == StudySubmission.Status.QC_REVIEW and submission.assigned_qc_reviewer:
                WorkflowService.send_assignment_notification(
                    submission, submission.assigned_qc_reviewer, 'qc_reviewer'
                )

            return {
                'success': True,
                'message': f'Successfully transitioned to {submission.get_status_display()}'
            }

        except ValueError as e:
            return {
                'success': False,
                'message': str(e)
            }

    @staticmethod
    def get_reviewer_statistics(user: User) -> Dict[str, Any]:
        """
        Get statistics for a reviewer's performance.

        Args:
            user: User instance

        Returns:
            Dict with statistics
        """
        stats = {
            'pending_reviews': 0,
            'completed_reviews': 0,
            'comments_made': 0,
            'corrections_made': 0,
            'avg_review_time': None,
        }

        if user.role == User.UserRole.TOXICOLOGIST:
            stats['pending_reviews'] = StudySubmission.objects.filter(
                assigned_toxicologist=user,
                status=StudySubmission.Status.TOXICOLOGIST_REVIEW
            ).count()

            completed = StudySubmission.objects.filter(
                assigned_toxicologist=user,
                tox_review_completed_at__isnull=False
            )
            stats['completed_reviews'] = completed.count()

        elif user.role == User.UserRole.SEND_EXPERT:
            stats['pending_reviews'] = StudySubmission.objects.filter(
                assigned_send_expert=user,
                status=StudySubmission.Status.SEND_EXPERT_REVIEW
            ).count()

            completed = StudySubmission.objects.filter(
                assigned_send_expert=user,
                send_review_completed_at__isnull=False
            )
            stats['completed_reviews'] = completed.count()

        elif user.role == User.UserRole.QC_REVIEWER:
            stats['pending_reviews'] = StudySubmission.objects.filter(
                assigned_qc_reviewer=user,
                status=StudySubmission.Status.QC_REVIEW
            ).count()

            completed = StudySubmission.objects.filter(
                assigned_qc_reviewer=user,
                qc_review_completed_at__isnull=False
            )
            stats['completed_reviews'] = completed.count()

        stats['comments_made'] = ReviewComment.objects.filter(reviewer=user).count()
        stats['corrections_made'] = AICorrection.objects.filter(corrected_by=user).count()

        return stats


class ConfidenceAnalysisService:
    """Service for analyzing extraction confidence scores"""

    @staticmethod
    def get_confidence_summary(submission: StudySubmission) -> Dict[str, Any]:
        """
        Get confidence score summary for a submission.

        Args:
            submission: StudySubmission instance

        Returns:
            Dict with confidence statistics
        """
        fields = ExtractedField.objects.filter(submission=submission)

        total_count = fields.count()
        if total_count == 0:
            return {
                'total_count': 0,
                'high_confidence': 0,
                'medium_confidence': 0,
                'low_confidence': 0,
                'requires_review': 0,
                'avg_confidence': 0.0,
            }

        high_count = fields.filter(confidence_score__gte=0.90).count()
        medium_count = fields.filter(
            confidence_score__gte=0.75,
            confidence_score__lt=0.90
        ).count()
        low_count = fields.filter(confidence_score__lt=0.75).count()
        requires_review_count = fields.filter(requires_review=True).count()

        avg_confidence = fields.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0.0

        return {
            'total_count': total_count,
            'high_confidence': high_count,
            'medium_confidence': medium_count,
            'low_confidence': low_count,
            'requires_review': requires_review_count,
            'avg_confidence': round(avg_confidence, 3),
            'high_percentage': round((high_count / total_count) * 100, 1),
            'medium_percentage': round((medium_count / total_count) * 100, 1),
            'low_percentage': round((low_count / total_count) * 100, 1),
        }

    @staticmethod
    def get_fields_by_confidence(
        submission: StudySubmission,
        level: str = 'low'
    ) -> List[ExtractedField]:
        """
        Get extracted fields filtered by confidence level.

        Args:
            submission: StudySubmission instance
            level: 'high', 'medium', or 'low'

        Returns:
            List of ExtractedField instances
        """
        fields = ExtractedField.objects.filter(submission=submission)

        if level == 'high':
            return fields.filter(confidence_score__gte=0.90).order_by('domain', 'variable')
        elif level == 'medium':
            return fields.filter(
                confidence_score__gte=0.75,
                confidence_score__lt=0.90
            ).order_by('domain', 'variable')
        elif level == 'low':
            return fields.filter(confidence_score__lt=0.75).order_by('confidence_score', 'domain')
        else:
            return fields.order_by('confidence_score')

    @staticmethod
    def get_domain_confidence_summary(submission: StudySubmission) -> Dict[str, Dict]:
        """
        Get confidence summary grouped by domain.

        Args:
            submission: StudySubmission instance

        Returns:
            Dict mapping domain codes to confidence statistics
        """
        fields = ExtractedField.objects.filter(submission=submission)

        # Get unique domains
        domains = fields.values_list('domain', flat=True).distinct()

        summary = {}
        for domain in domains:
            domain_fields = fields.filter(domain=domain)
            avg_conf = domain_fields.aggregate(Avg('confidence_score'))['confidence_score__avg']

            summary[domain] = {
                'count': domain_fields.count(),
                'avg_confidence': round(avg_conf or 0.0, 3),
                'requires_review': domain_fields.filter(requires_review=True).count(),
            }

        return summary


class TraceabilityService:
    """Service for managing data provenance and traceability"""

    @staticmethod
    def create_provenance_record(
        submission: StudySubmission,
        domain: str,
        variable: str,
        value: str,
        pdf_page: int,
        extraction_method: str = 'AI',
        **kwargs
    ) -> DataProvenance:
        """
        Create a data provenance record for traceability.

        Args:
            submission: StudySubmission instance
            domain: SEND domain code
            variable: SEND variable name
            value: Extracted value
            pdf_page: PDF page number
            extraction_method: Method used ('AI', 'MANUAL', 'CORRECTED')
            **kwargs: Additional fields (pdf_table, pdf_row, pdf_column, etc.)

        Returns:
            DataProvenance instance
        """
        provenance = DataProvenance.objects.create(
            submission=submission,
            domain=domain,
            variable=variable,
            value=value,
            pdf_page=pdf_page,
            extraction_method=extraction_method,
            **kwargs
        )
        return provenance

    @staticmethod
    def get_traceability_report(submission: StudySubmission) -> Dict[str, Any]:
        """
        Generate comprehensive traceability report for a submission.

        Args:
            submission: StudySubmission instance

        Returns:
            Dict with traceability information
        """
        provenance_records = DataProvenance.objects.filter(
            submission=submission
        ).order_by('pdf_page', 'domain')

        report = {
            'total_records': provenance_records.count(),
            'by_domain': {},
            'by_page': {},
            'by_method': {},
        }

        # Group by domain
        for domain in provenance_records.values_list('domain', flat=True).distinct():
            domain_records = provenance_records.filter(domain=domain)
            report['by_domain'][domain] = {
                'count': domain_records.count(),
                'records': list(domain_records.values(
                    'variable', 'value', 'pdf_page', 'extraction_method', 'confidence_score'
                ))
            }

        # Group by page
        for page in provenance_records.values_list('pdf_page', flat=True).distinct():
            page_records = provenance_records.filter(pdf_page=page)
            report['by_page'][page] = {
                'count': page_records.count(),
                'domains': list(page_records.values_list('domain', flat=True).distinct())
            }

        # Group by extraction method
        for method in provenance_records.values_list('extraction_method', flat=True).distinct():
            method_records = provenance_records.filter(extraction_method=method)
            report['by_method'][method] = method_records.count()

        return report


class CorrectionAnalyticsService:
    """Service for analyzing AI corrections and training feedback"""

    @staticmethod
    def get_correction_patterns(domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze correction patterns to identify common AI issues.

        Args:
            domain: Optional domain filter

        Returns:
            Dict with correction pattern analysis
        """
        corrections = AICorrection.objects.all()
        if domain:
            corrections = corrections.filter(domain=domain)

        total_count = corrections.count()

        # Group by correction type
        by_type = {}
        for correction_type in corrections.values_list('correction_type', flat=True).distinct():
            count = corrections.filter(correction_type=correction_type).count()
            by_type[correction_type] = {
                'count': count,
                'percentage': round((count / total_count) * 100, 1) if total_count > 0 else 0
            }

        # Group by domain
        by_domain = {}
        for dom in corrections.values_list('domain', flat=True).distinct():
            domain_corrections = corrections.filter(domain=dom)
            by_domain[dom] = {
                'count': domain_corrections.count(),
                'most_common_type': domain_corrections.values('correction_type').annotate(
                    count=Count('correction_type')
                ).order_by('-count').first()
            }

        # Training data status
        training_ready = corrections.filter(added_to_training=False).count()
        already_exported = corrections.filter(added_to_training=True).count()

        return {
            'total_corrections': total_count,
            'by_type': by_type,
            'by_domain': by_domain,
            'training_ready': training_ready,
            'already_exported': already_exported,
        }

    @staticmethod
    def export_training_dataset(output_format: str = 'csv') -> str:
        """
        Export corrections as training dataset.

        Args:
            output_format: 'csv' or 'json'

        Returns:
            File path to exported dataset
        """
        import csv
        import json
        from datetime import datetime
        import os

        corrections = AICorrection.objects.filter(added_to_training=False)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'training_dataset_{timestamp}.{output_format}'
        filepath = os.path.join(settings.MEDIA_ROOT, 'training_data', filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if output_format == 'csv':
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'domain', 'variable', 'original_extraction', 'corrected_value',
                    'correction_reason', 'correction_type', 'ai_confidence_before'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for correction in corrections:
                    writer.writerow({
                        'domain': correction.domain,
                        'variable': correction.variable,
                        'original_extraction': correction.original_extraction,
                        'corrected_value': correction.corrected_value,
                        'correction_reason': correction.correction_reason,
                        'correction_type': correction.correction_type,
                        'ai_confidence_before': correction.ai_confidence_before or '',
                    })

        elif output_format == 'json':
            data = []
            for correction in corrections:
                data.append({
                    'domain': correction.domain,
                    'variable': correction.variable,
                    'original_extraction': correction.original_extraction,
                    'corrected_value': correction.corrected_value,
                    'correction_reason': correction.correction_reason,
                    'correction_type': correction.correction_type,
                    'ai_confidence_before': correction.ai_confidence_before,
                })

            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2)

        # Mark corrections as exported
        corrections.update(added_to_training=True, training_export_date=datetime.now())

        return filepath
