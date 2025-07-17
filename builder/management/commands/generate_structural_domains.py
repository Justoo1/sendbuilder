"""
Django management command to generate structural domains (TE, SE, TX)

Place this file in: builder/management/commands/generate_structural_domains.py

Usage:
    python manage.py generate_structural_domains --study-id 1
    python manage.py generate_structural_domains --all-studies
    python manage.py generate_structural_domains --study-id 1 --force
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from builder.models import Study, StudyContent, DetectedDomain, Domain
from builder.utils.structural_domain_generator import StructuralDomainGenerator


class Command(BaseCommand):
    help = 'Generate structural domains (TE, SE, TX) for studies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--study-id',
            type=int,
            help='Generate structural domains for specific study ID'
        )
        parser.add_argument(
            '--all-studies',
            action='store_true',
            help='Generate structural domains for all studies'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration even if domains already exist'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without actually creating domains'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed analysis information'
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("SEND Structural Domain Generator"))
        self.stdout.write("=" * 60)
        
        # Validate arguments
        if not options['study_id'] and not options['all_studies']:
            raise CommandError('Either --study-id or --all-studies must be specified')
        
        if options['study_id'] and options['all_studies']:
            raise CommandError('Cannot specify both --study-id and --all-studies')
        
        # Get studies to process
        if options['study_id']:
            try:
                studies = [Study.objects.get(study_id=options['study_id'])]
            except Study.DoesNotExist:
                raise CommandError(f"Study with ID {options['study_id']} not found")
        else:
            studies = Study.objects.all()
            
        if not studies:
            self.stdout.write(self.style.WARNING("No studies found"))
            return
            
        self.stdout.write(f"Found {len(studies)} study(ies) to process")
        
        # Initialize generator
        generator = StructuralDomainGenerator(StudyContent, DetectedDomain, Domain)
        
        # Process each study
        total_generated = 0
        for study in studies:
            self.stdout.write(f"\n{'-' * 40}")
            self.stdout.write(f"Processing Study: {study.study_id} - {study.title[:50]}...")
            
            if options['dry_run']:
                results = self._dry_run_analysis(generator, study)
            else:
                results = generator.generate_missing_structural_domains(
                    study, 
                    force_regenerate=options['force']
                )
            
            # Display results
            for domain_code, success in results.items():
                if success:
                    status = self.style.SUCCESS("✓ Generated/Exists")
                    if not options['dry_run']:
                        total_generated += 1
                else:
                    status = self.style.ERROR("✗ Not generated")
                    
                self.stdout.write(f"  {domain_code}: {status}")
            
            # Show existing detections for context
            if options['verbose']:
                self._show_existing_detections(study)
        
        # Summary
        self.stdout.write(f"\n{'=' * 60}")
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("DRY RUN COMPLETED - No changes made"))
        else:
            self.stdout.write(self.style.SUCCESS(f"COMPLETED - {total_generated} domains generated"))
        self.stdout.write(f"{'=' * 60}")
        
        # Recommendations
        self._show_recommendations()

    def _dry_run_analysis(self, generator, study):
        """Perform dry run analysis without creating domains"""
        self.stdout.write("  [DRY RUN] Analyzing content...")
        
        try:
            # Get study content
            study_pages = StudyContent.objects.filter(study=study)
            if not study_pages.exists():
                self.stdout.write("    No study content found")
                return {'TE': False, 'SE': False, 'TX': False}
            
            content = "\n".join([page.content for page in study_pages])
            
            # Analyze each domain
            results = {}
            
            # TE Analysis
            te_score = self._analyze_te_patterns(content)
            results['TE'] = te_score >= 15
            self.stdout.write(f"    TE analysis score: {te_score} (threshold: 15)")
            
            # SE Analysis  
            se_score, subjects = self._analyze_se_patterns(content)
            results['SE'] = se_score >= 20 and subjects >= 5
            self.stdout.write(f"    SE analysis score: {se_score} (threshold: 20), subjects: {subjects}")
            
            # TX Analysis
            tx_score, doses, groups = self._analyze_tx_patterns(content)
            results['TX'] = tx_score >= 25 and doses >= 2 and groups >= 2
            self.stdout.write(f"    TX analysis score: {tx_score} (threshold: 25), doses: {doses}, groups: {groups}")
            
            return results
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Error in analysis: {e}"))
            return {'TE': False, 'SE': False, 'TX': False}

    def _analyze_te_patterns(self, content):
        """Analyze TE patterns and return score"""
        import re
        
        te_patterns = [
            (r'(?i)study.{0,20}schedule', 3),
            (r'(?i)experimental.{0,20}design', 3),
            (r'(?i)acclimation.*\d+.*days?', 2),
            (r'(?i)dosing.*\d+.*days?', 2),
            (r'(?i)consecutive.*days?', 2),
            (r'(?i)necropsy', 2),
            (r'(?i)day.{0,10}[-]?\d+', 1),
        ]
        
        score = 0
        for pattern, weight in te_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            score += matches * weight
            
        return score

    def _analyze_se_patterns(self, content):
        """Analyze SE patterns and return score and subject count"""
        import re
        
        se_patterns = [
            (r'(?i)group.{0,10}\d+', 2),
            (r'(?i)animal.{0,10}\d{4}', 3),
            (r'(?i)randomization', 3),
            (r'(?i)assignment', 2),
        ]
        
        score = 0
        for pattern, weight in se_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            score += matches * weight
        
        # Count unique subjects
        subject_ids = re.findall(r'\b\d{4}\b', content)
        unique_subjects = len(set(subject_ids))
        
        if unique_subjects >= 5:
            score += unique_subjects
            
        return score, unique_subjects

    def _analyze_tx_patterns(self, content):
        """Analyze TX patterns and return score, dose count, and group count"""
        import re
        
        tx_patterns = [
            (r'(?i)group.{0,10}\d+.*mg/kg', 4),
            (r'(?i)vehicle.*control', 3),
            (r'(?i)dose.{0,20}level', 3),
            (r'(?i)treatment.{0,20}group', 2),
            (r'(?i)mg/kg/day', 1),
        ]
        
        score = 0
        for pattern, weight in tx_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            score += matches * weight
        
        # Count doses and groups
        dose_matches = re.findall(r'\d+\.?\d*\s*mg/kg', content, re.IGNORECASE)
        unique_doses = len(set(dose_matches))
        
        group_matches = re.findall(r'group\s*\d+', content, re.IGNORECASE)
        unique_groups = len(set([match.lower() for match in group_matches]))
        
        if unique_doses >= 2:
            score += unique_doses * 3
        if unique_groups >= 2:
            score += unique_groups * 2
            
        return score, unique_doses, unique_groups

    def _show_existing_detections(self, study):
        """Show existing domain detections for a study"""
        detections = DetectedDomain.objects.filter(study=study).select_related('domain')
        
        if detections.exists():
            self.stdout.write("  Existing detections:")
            for detection in detections:
                pages = detection.page if detection.page else []
                page_info = f"pages: {pages}" if pages else "no pages"
                self.stdout.write(f"    {detection.domain.code}: confidence {detection.confident_score}% ({page_info})")
        else:
            self.stdout.write("  No existing detections found")

    def _show_recommendations(self):
        """Show recommendations for next steps"""
        self.stdout.write("\nRecommendations:")
        self.stdout.write("-" * 20)
        self.stdout.write("1. Check generated domains in admin interface")
        self.stdout.write("2. Run domain extraction for new domains:")
        self.stdout.write("   python manage.py extract_domains --study-id <ID> --domain TE")
        self.stdout.write("   python manage.py extract_domains --study-id <ID> --domain SE")
        self.stdout.write("   python manage.py extract_domains --study-id <ID> --domain TX")
        self.stdout.write("3. Validate with Pinnacle 21 to check improvements")
        self.stdout.write("4. Update domains.json if TX domain missing:")
        self.stdout.write("   python manage.py load_domains domains.json")
        
        # Check if TX domain exists
        try:
            Domain.objects.get(code='TX')
        except Domain.DoesNotExist:
            self.stdout.write(self.style.WARNING("\nWARNING: TX domain not found in database!"))
            self.stdout.write("Add TX domain to domains.json and run: python manage.py load_domains domains.json")

    def _check_prerequisites(self):
        """Check if prerequisites are met"""
        issues = []
        
        # Check if required domains exist
        required_domains = ['TE', 'SE', 'TX']
        for domain_code in required_domains:
            try:
                Domain.objects.get(code=domain_code)
            except Domain.DoesNotExist:
                issues.append(f"Domain {domain_code} not found in database")
        
        if issues:
            self.stdout.write(self.style.ERROR("Prerequisites not met:"))
            for issue in issues:
                self.stdout.write(f"  - {issue}")
            self.stdout.write("\nRun: python manage.py load_domains domains.json")
            return False
            
        return True