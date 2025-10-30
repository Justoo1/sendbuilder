# SEND Builder - Multi-Layer Validation Workflow Implementation Guide

## Overview

This guide covers the implementation of an enterprise-grade, multi-layer human validation workflow system for the SEND Builder application. The system ensures FDA submission quality while maintaining AI efficiency through role-based review stages, confidence scoring, and complete data traceability.

## What's Been Implemented

### ✅ Core Features Completed

#### 1. **Custom User Model with Roles** ✓
- Extended Django's `AbstractUser` with role-based access control
- **Roles**: ADMIN, TOXICOLOGIST, SEND_EXPERT, QC_REVIEWER
- Additional fields: department, specialization, availability status
- Location: [`builder/models.py`](builder/models.py) (lines 74-130)

#### 2. **Workflow State Machine** ✓
- `StudySubmission` model with 7 workflow states:
  - UPLOADED → AI_PROCESSING → TOXICOLOGIST_REVIEW → SEND_EXPERT_REVIEW → QC_REVIEW → APPROVED/REJECTED
- Automatic reviewer assignments based on workload
- Timestamp tracking for each workflow stage
- State transition validation with `can_transition_to()` and `transition_to()` methods
- Location: [`builder/models.py`](builder/models.py) (lines 340-508)

#### 3. **Confidence Scoring System** ✓
- `ExtractedField` model for individual data point tracking
- Confidence scores (0.0-1.0) with automatic flagging (`< 0.85` requires review)
- Three-level classification: High (≥0.90), Medium (0.75-0.89), Low (<0.75)
- Bootstrap color-coding for UI (green/yellow/red)
- Location: [`builder/models.py`](builder/models.py) (lines 511-624)

#### 4. **Review & Feedback System** ✓
- `ReviewComment` model with severity levels (CRITICAL, MAJOR, MINOR, INFO)
- Domain and variable-specific comments
- Resolution tracking with notes
- Reviewer assignment and comment history
- Location: [`builder/models.py`](builder/models.py) (lines 627-737)

#### 5. **AI Training Feedback Loop** ✓
- `AICorrection` model tracking all human corrections
- Captures: original extraction, corrected value, reason, correction type
- Export functionality for training datasets (CSV/JSON)
- Training data status tracking
- Location: [`builder/models.py`](builder/models.py) (lines 740-825)

#### 6. **Data Traceability System** ✓
- `DataProvenance` model linking data to PDF sources
- Tracks: page number, table, row, column, coordinates
- Extraction method tagging (AI/Manual/Corrected)
- Complete audit trail for FDA compliance
- Location: [`builder/models.py`](builder/models.py) (lines 828-972)

#### 7. **Django Admin Configuration** ✓
- Custom admin interfaces for all workflow models
- Role-based user administration
- Submission workflow management
- Confidence score filtering
- Training data export actions
- Location: [`builder/admin.py`](builder/admin.py)

#### 8. **Workflow Service Functions** ✓
- Automatic reviewer assignment by workload
- Email notifications for assignments
- Workflow transition management
- Statistics and analytics
- Confidence analysis utilities
- Correction pattern analysis
- Traceability report generation
- Location: [`builder/utils/workflow_services.py`](builder/utils/workflow_services.py)

#### 9. **Database Migrations** ✓
- All models migrated to PostgreSQL schema
- Custom migration helper script for User model transition
- Location: [`builder/migrations/0006_*.py`](builder/migrations/)

#### 10. **Settings Configuration** ✓
- `AUTH_USER_MODEL = 'builder.User'`
- Email backend configuration
- Login/logout URLs
- Location: [`sendbuilder/settings.py`](sendbuilder/settings.py) (lines 132-149)

---

## Database Schema

### Core Workflow Tables

```
builder_user (Custom User)
├── Standard Django fields (username, email, password, etc.)
├── role (ADMIN, TOXICOLOGIST, SEND_EXPERT, QC_REVIEWER)
├── department, specialization
└── is_available (for auto-assignment)

builder_studysubmission (Workflow Management)
├── study (OneToOne → Study)
├── submission_id (unique identifier)
├── status (workflow state)
├── assigned_toxicologist (FK → User)
├── assigned_send_expert (FK → User)
├── assigned_qc_reviewer (FK → User)
├── priority (1-5)
├── timestamps for each workflow stage
└── rejection_reason, notes

builder_extractedfield (Confidence Scoring)
├── submission (FK → StudySubmission)
├── domain, variable, value
├── confidence_score (0.0-1.0)
├── requires_review (auto-flagged if < 0.85)
├── reviewed, reviewed_by, reviewed_at
└── is_corrected, original_value

builder_reviewcomment (Feedback Tracking)
├── submission (FK → StudySubmission)
├── reviewer (FK → User)
├── domain, variable (optional)
├── comment, severity
├── resolved, resolved_by, resolved_at
└── resolution_notes

builder_aicorrection (Training Feedback)
├── submission (FK → StudySubmission)
├── domain, variable
├── original_extraction, corrected_value
├── correction_reason, correction_type
├── corrected_by (FK → User)
├── added_to_training
└── ai_confidence_before

builder_dataprovenance (Traceability)
├── submission (FK → StudySubmission)
├── domain, variable, value
├── pdf_page, pdf_table, pdf_row, pdf_column
├── pdf_coordinates (JSON)
├── extraction_method (AI/MANUAL/CORRECTED)
├── extracted_by, reviewed_by
└── source_text, confidence_score
```

---

## Migration Instructions

### ⚠️ IMPORTANT: User Model Migration

Since we're switching from Django's default `auth.User` to a custom `builder.User` model, you need to migrate carefully.

### Option 1: Fresh Start (Recommended for Development)

```bash
# 1. Run the migration helper script
uv run python migrate_to_custom_user.py --fresh-start

# This will:
# - Drop all existing tables (DATA WILL BE DELETED!)
# - Remove old migration files
# - Create fresh migrations
# - Apply all migrations
# - Prompt you to create a superuser

# 2. Create additional users via Django admin
# http://localhost:8000/admin/builder/user/add/
```

### Option 2: Check Status First

```bash
# Check current migration status
uv run python migrate_to_custom_user.py --status

# Create database backup (PostgreSQL)
pg_dump -U postgres -d builder > backup_$(date +%Y%m%d_%H%M%S).sql

# Then proceed with fresh start
uv run python migrate_to_custom_user.py --fresh-start
```

### Post-Migration Steps

1. **Create Test Users**:
   - Log into Django admin: `http://localhost:8000/admin/`
   - Create users with different roles:
     - 1 Toxicologist
     - 1 SEND Expert
     - 1 QC Reviewer
     - 1 Admin (already created by script)

2. **Verify Models**:
   ```bash
   uv run manage.py shell
   ```
   ```python
   from builder.models import User, StudySubmission, ExtractedField
   print(User.objects.count())  # Should show your created users
   print(User.objects.filter(role='TOXICOLOGIST'))
   ```

3. **Test Workflow**:
   - Upload a study PDF
   - Create a `StudySubmission` linked to the study
   - Assign reviewers
   - Test status transitions

---

## Usage Examples

### Creating a Workflow Submission

```python
from builder.models import Study, StudySubmission, User
from builder.utils.workflow_services import WorkflowService

# Get or create study
study = Study.objects.get(study_number='TOX-2024-001')

# Create submission
submission = StudySubmission.objects.create(
    study=study,
    priority=2  # 1=Critical, 5=Low
)
# submission_id auto-generated as "SUB-TOX-2024-001-20251030120000"

# Auto-assign reviewers
result = WorkflowService.assign_reviewers(submission, auto_assign=True)
print(f"Assigned toxicologist: {result['toxicologist']}")
print(f"Assigned SEND expert: {result['send_expert']}")
print(f"Assigned QC reviewer: {result['qc_reviewer']}")

# Transition to AI processing
WorkflowService.transition_workflow(
    submission=submission,
    new_status=StudySubmission.Status.AI_PROCESSING,
    user=request.user
)
```

### Recording Extracted Fields with Confidence

```python
from builder.models import ExtractedField

# After AI extraction, create field records
field = ExtractedField.objects.create(
    submission=submission,
    domain='DM',
    variable='STUDYID',
    value='TOX-2024-001',
    confidence_score=0.95  # High confidence
)
# requires_review automatically set to False (confidence >= 0.85)

# Low confidence field
low_conf_field = ExtractedField.objects.create(
    submission=submission,
    domain='BW',
    variable='BWSTRESN',
    value='23.4',
    confidence_score=0.72  # Low confidence
)
# requires_review automatically set to True (confidence < 0.85)
```

### Adding Review Comments

```python
from builder.models import ReviewComment

# Toxicologist adds a critical comment
comment = ReviewComment.objects.create(
    submission=submission,
    reviewer=toxicologist_user,
    domain='LB',
    variable='LBTESTCD',
    comment='Lab test codes do not match CDISC CT. Please verify against the controlled terminology.',
    severity=ReviewComment.Severity.CRITICAL
)

# Resolve the comment later
comment.resolve(
    user=send_expert_user,
    notes='Updated all LBTESTCD values to match CDISC SEND CT 2023-12-15.'
)
```

### Tracking AI Corrections

```python
from builder.models import AICorrection

# Record a correction made by reviewer
correction = AICorrection.objects.create(
    submission=submission,
    domain='DM',
    variable='SEX',
    original_extraction='Male',
    corrected_value='M',
    correction_reason='SEND requires coded values: M=Male, F=Female, not full text.',
    correction_type='format',
    corrected_by=reviewer_user,
    ai_confidence_before=0.88
)

# Mark for training
correction.mark_as_training_data()
```

### Creating Provenance Records

```python
from builder.utils.workflow_services import TraceabilityService

# Link extracted data to PDF source
provenance = TraceabilityService.create_provenance_record(
    submission=submission,
    domain='BW',
    variable='BWSTRESN',
    value='23.4',
    pdf_page=15,
    pdf_table='Table 3: Body Weights',
    pdf_row=7,
    pdf_column='Week 4',
    extraction_method='AI',
    confidence_score=0.92
)

# Get traceability report
report = TraceabilityService.get_traceability_report(submission)
print(f"Total provenance records: {report['total_records']}")
print(f"Data by domain: {report['by_domain']}")
```

### Analyzing Confidence Scores

```python
from builder.utils.workflow_services import ConfidenceAnalysisService

# Get confidence summary
summary = ConfidenceAnalysisService.get_confidence_summary(submission)
print(f"Average confidence: {summary['avg_confidence']}")
print(f"High confidence fields: {summary['high_confidence']} ({summary['high_percentage']}%)")
print(f"Fields requiring review: {summary['requires_review']}")

# Get low confidence fields for review
low_conf_fields = ConfidenceAnalysisService.get_fields_by_confidence(
    submission=submission,
    level='low'
)
for field in low_conf_fields:
    print(f"{field.domain}.{field.variable}: {field.value} (conf: {field.confidence_score})")
```

### Exporting Training Data

```python
from builder.utils.workflow_services import CorrectionAnalyticsService

# Get correction patterns
patterns = CorrectionAnalyticsService.get_correction_patterns(domain='DM')
print(f"Total corrections: {patterns['total_corrections']}")
print(f"By type: {patterns['by_type']}")
print(f"Ready for training: {patterns['training_ready']}")

# Export corrections as training dataset
filepath = CorrectionAnalyticsService.export_training_dataset(output_format='csv')
print(f"Training dataset exported to: {filepath}")
```

---

## Workflow State Machine

```
UPLOADED
   ↓ (upload_study_pdf)
AI_PROCESSING
   ↓ (ai_extraction_complete)
   ├→ REJECTED (if AI fails)
   └→ TOXICOLOGIST_REVIEW
       ↓ (toxicologist_approves)
       ├→ REJECTED (if toxicologist rejects)
       └→ SEND_EXPERT_REVIEW
           ↓ (send_expert_approves)
           ├→ REJECTED (if SEND expert rejects)
           ├→ TOXICOLOGIST_REVIEW (if needs re-review)
           └→ QC_REVIEW
               ↓ (qc_reviewer_approves)
               ├→ APPROVED (final state)
               ├→ REJECTED (if QC rejects)
               └→ SEND_EXPERT_REVIEW (if needs re-review)

REJECTED
   └→ TOXICOLOGIST_REVIEW (can restart)
```

### Valid Transitions

- `UPLOADED` → `AI_PROCESSING`
- `AI_PROCESSING` → `TOXICOLOGIST_REVIEW`, `REJECTED`
- `TOXICOLOGIST_REVIEW` → `SEND_EXPERT_REVIEW`, `REJECTED`
- `SEND_EXPERT_REVIEW` → `QC_REVIEW`, `TOXICOLOGIST_REVIEW`, `REJECTED`
- `QC_REVIEW` → `APPROVED`, `SEND_EXPERT_REVIEW`, `REJECTED`
- `REJECTED` → `TOXICOLOGIST_REVIEW`
- `APPROVED` → (terminal state)

---

## Next Steps (To Be Implemented)

### 🔲 Views & Templates
1. Role-based dashboard views
2. Toxicologist review interface
3. SEND Expert review interface
4. QC Reviewer interface
5. Confidence-based extraction view
6. Traceability report view
7. AI correction tracking UI
8. Analytics dashboard

### 🔲 Forms
1. `ReviewCommentForm`
2. `AssignReviewerForm`
3. `CorrectionForm`
4. `ProvenanceForm`

### 🔲 URL Configuration
1. `/workflow/dashboard/` - Role-based dashboard
2. `/workflow/submission/<id>/review/` - Review interface
3. `/workflow/submission/<id>/confidence/` - Confidence view
4. `/workflow/submission/<id>/traceability/` - Traceability report
5. `/workflow/analytics/corrections/` - Correction analytics

### 🔲 Permissions & Decorators
1. `@role_required(role='TOXICOLOGIST')`
2. `@can_review_submission`
3. `RolePermissionMixin` for class-based views

### 🔲 Email Templates
1. `emails/reviewer_assignment.html`
2. `emails/workflow_status_change.html`
3. `emails/critical_issue_alert.html`

### 🔲 Integration with Existing Extraction Pipeline
1. Update `ExtractionPipeline.extract_domain()` to:
   - Create `ExtractedField` records
   - Calculate confidence scores
   - Create `DataProvenance` records
   - Link to `StudySubmission`

### 🔲 Testing
1. Unit tests for workflow transitions
2. Integration tests for reviewer assignment
3. Test data fixtures
4. API endpoint tests

---

## File Structure

```
sendbuilder/
├── builder/
│   ├── models.py                    # ✅ All workflow models
│   ├── admin.py                     # ✅ Django admin configuration
│   ├── views.py                     # 🔲 To be updated with workflow views
│   ├── forms.py                     # 🔲 To be created
│   ├── urls.py                      # 🔲 To be updated
│   ├── utils/
│   │   ├── workflow_services.py     # ✅ Workflow utility functions
│   │   ├── extractions/
│   │   │   └── pipeline.py          # 🔲 To be updated with confidence scoring
│   │   └── ...
│   ├── templates/
│   │   ├── workflow/                # 🔲 To be created
│   │   │   ├── dashboard.html
│   │   │   ├── review_interface.html
│   │   │   └── ...
│   │   └── emails/                  # 🔲 To be created
│   └── migrations/
│       └── 0006_user_studysubmission_*.py  # ✅ Generated
├── sendbuilder/
│   └── settings.py                  # ✅ Updated with AUTH_USER_MODEL
├── migrate_to_custom_user.py        # ✅ Migration helper script
└── WORKFLOW_IMPLEMENTATION_GUIDE.md # ✅ This file
```

---

## Configuration

### Email Settings (settings.py)

```python
# Development: Print emails to console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Production: Configure SMTP
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'sendbuilder@example.com'
```

### User Model Settings

```python
AUTH_USER_MODEL = 'builder.User'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
```

---

## API Reference

### WorkflowService

- `assign_reviewers(submission, auto_assign=True)` - Auto-assign reviewers by workload
- `send_assignment_notification(submission, reviewer, role)` - Email notification
- `transition_workflow(submission, new_status, user, reason=None)` - State transition
- `get_reviewer_statistics(user)` - Get reviewer performance stats

### ConfidenceAnalysisService

- `get_confidence_summary(submission)` - Overall confidence statistics
- `get_fields_by_confidence(submission, level)` - Filter by confidence level
- `get_domain_confidence_summary(submission)` - Per-domain statistics

### TraceabilityService

- `create_provenance_record(...)` - Create traceability record
- `get_traceability_report(submission)` - Generate full report

### CorrectionAnalyticsService

- `get_correction_patterns(domain=None)` - Analyze correction patterns
- `export_training_dataset(output_format)` - Export to CSV/JSON

---

## Troubleshooting

### Migration Issues

**Error: "app 'builder' doesn't provide model 'user'"**
- Solution: Run `uv run python migrate_to_custom_user.py --fresh-start`

**Error: Database connection failed**
- Check PostgreSQL is running: `pg_ctl status`
- Verify credentials in `settings.py`

### Import Errors

**Error: Cannot import User from django.contrib.auth.models**
- Update imports to use: `from builder.models import User`
- Or use: `from django.contrib.auth import get_user_model; User = get_user_model()`

---

## Support & Documentation

- **Django Documentation**: https://docs.djangoproject.com/
- **CDISC SEND**: https://www.cdisc.org/standards/foundational/send
- **FDA Guidance**: https://www.fda.gov/regulatory-information

---

## Version History

- **v1.0** (2025-10-30): Initial implementation
  - Custom User model with roles
  - Complete workflow state machine
  - Confidence scoring system
  - Review & feedback tracking
  - AI training feedback loop
  - Data traceability
  - Admin interfaces
  - Utility services

---

## License

Copyright © 2025 SEND Builder Project. All rights reserved.
