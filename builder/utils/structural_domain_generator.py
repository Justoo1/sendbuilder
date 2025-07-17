"""
Structural Domain Generator for SEND domains TE, SE, TX

This module generates structural domains (TE, SE, TX) by analyzing 
study design patterns rather than relying only on direct text matching.

Place this file in: builder/utils/structural_domain_generator.py
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from django.db import transaction

logger = logging.getLogger(__name__)


class StructuralDomainGenerator:
    """
    Generates TE, SE, TX domains from study design information
    rather than relying only on pattern matching
    """
    
    def __init__(self, study_content_model, detected_domain_model, domain_model):
        self.StudyContent = study_content_model
        self.DetectedDomain = detected_domain_model
        self.Domain = domain_model
    
    def generate_missing_structural_domains(self, study, force_regenerate=False) -> Dict[str, bool]:
        """
        Generate TE, SE, TX domains by analyzing study structure
        
        Args:
            study: Study instance
            force_regenerate: If True, regenerate even if domains already exist
            
        Returns:
            Dict with generation results for each domain
        """
        results = {
            'TE': False,
            'SE': False, 
            'TX': False
        }
        
        try:
            logger.info(f"Starting structural domain generation for study {study.study_id}")
            
            # Get all study content
            study_pages = self.StudyContent.objects.filter(study=study)
            if not study_pages.exists():
                logger.warning("No study content found for structural domain generation")
                return results
            
            full_content = "\n".join([page.content for page in study_pages])
            
            # Check which domains already exist (unless force regenerate)
            existing_domains = set()
            if not force_regenerate:
                existing_detections = self.DetectedDomain.objects.filter(
                    study=study, 
                    domain__code__in=['TE', 'SE', 'TX']
                ).values_list('domain__code', flat=True)
                existing_domains = set(existing_detections)
                logger.info(f"Existing structural domains: {existing_domains}")
            
            # Generate each structural domain
            if 'TE' not in existing_domains:
                results['TE'] = self._generate_te_domain(study, full_content)
            else:
                results['TE'] = True
                logger.info("TE domain already exists")
                
            if 'SE' not in existing_domains:
                results['SE'] = self._generate_se_domain(study, full_content)
            else:
                results['SE'] = True
                logger.info("SE domain already exists")
                
            if 'TX' not in existing_domains:
                results['TX'] = self._generate_tx_domain(study, full_content)
            else:
                results['TX'] = True
                logger.info("TX domain already exists")
            
            logger.info(f"Structural domain generation completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error generating structural domains: {e}")
            return results
    
    def _generate_te_domain(self, study, content: str) -> bool:
        """Generate TE domain from study design elements"""
        try:
            logger.info("Analyzing content for TE domain generation")
            
            # Look for study design indicators with specific patterns
            te_indicators = [
                (r'(?i)study.{0,20}schedule', 3),              # High value indicators
                (r'(?i)experimental.{0,20}design', 3),
                (r'(?i)acclimation.*\d+.*days?', 2),           # Medium value indicators
                (r'(?i)dosing.*\d+.*days?', 2),
                (r'(?i)consecutive.*days?', 2),
                (r'(?i)necropsy', 2),
                (r'(?i)day.{0,10}[-]?\d+', 1),                 # Lower value indicators
                (r'(?i)screening.*period', 1),
                (r'(?i)treatment.*period', 1),
                (r'(?i)recovery.*period', 1),
                (r'(?i)study.{0,20}duration', 2),
                (r'(?i)timeline', 1),
                (r'(?i)epoch', 1),
                (r'(?i)study.{0,20}conduct', 1),
                (r'(?i)treatment.{0,20}regimen', 2)
            ]
            
            # Calculate weighted score
            total_score = 0
            evidence_items = []
            
            for pattern, weight in te_indicators:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    score = len(matches) * weight
                    total_score += score
                    evidence_items.append(f"{len(matches)} instances of {pattern.split(')')[1]}")
                    logger.debug(f"TE pattern '{pattern}': {len(matches)} matches (score: {score})")
            
            # Look for specific study phase descriptions
            phase_patterns = [
                r'(?i)acclimation.*\d+.*days?',
                r'(?i)dosing.*\d+.*consecutive.*days?',
                r'(?i)study.*day.*1.*dosing',
                r'(?i)necropsy.*day.*\d+',
                r'(?i)observation.*period'
            ]
            
            phase_count = sum(
                len(re.findall(pattern, content, re.IGNORECASE))
                for pattern in phase_patterns
            )
            
            if phase_count >= 2:
                total_score += phase_count * 2
                evidence_items.append(f"{phase_count} study phases identified")
            
            # Threshold for TE generation (adjusted based on analysis)
            te_threshold = 15
            confidence = min(95, 60 + (total_score * 2))
            
            logger.info(f"TE domain analysis: score={total_score}, threshold={te_threshold}, confidence={confidence}")
            
            if total_score >= te_threshold:
                evidence_text = f"Generated from study design structure (score: {total_score}): {'; '.join(evidence_items[:3])}"
                return self._create_domain_detection(study, 'TE', confidence, evidence_text)
            else:
                logger.info(f"TE domain not generated: score {total_score} below threshold {te_threshold}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error generating TE domain: {e}")
            return False
    
    def _generate_se_domain(self, study, content: str) -> bool:
        """Generate SE domain from subject assignment information"""
        try:
            logger.info("Analyzing content for SE domain generation")
            
            # Look for subject/animal assignment patterns with weights
            subject_indicators = [
                (r'(?i)group.{0,10}\d+', 2),                   # Group 1, Group 2, etc.
                (r'(?i)animal.{0,10}\d{4}', 3),                # Animal 1001, 2001, etc.
                (r'(?i)subject.{0,10}\d+', 3),                 # Subject numbers
                (r'(?i)randomization', 3),                      # Randomization procedures
                (r'(?i)assignment', 2),                         # Assignment procedures
                (r'(?i)\d{4}.*group', 2),                      # Subject-group relationships
                (r'(?i)treatment.{0,20}group', 1),             # Treatment group assignments
                (r'(?i)animal.{0,20}receipt', 2),              # Animal receipt procedures
                (r'(?i)identification.{0,20}system', 2),       # ID system
                (r'(?i)cage.{0,20}cards', 1),                  # Housing assignments
                (r'(?i)individual.{0,20}animal', 1),           # Individual references
            ]
            
            # Calculate weighted score
            total_score = 0
            evidence_items = []
            
            for pattern, weight in subject_indicators:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    score = len(matches) * weight
                    total_score += score
                    evidence_items.append(f"{len(matches)} instances of subject patterns")
                    logger.debug(f"SE pattern '{pattern}': {len(matches)} matches (score: {score})")
            
            # Look for multiple subject IDs (indicating subject data exists)
            subject_id_matches = re.findall(r'\b\d{4}\b', content)  # 4-digit subject IDs
            unique_subjects = len(set(subject_id_matches))
            
            if unique_subjects >= 5:  # Minimum number of subjects
                total_score += unique_subjects
                evidence_items.append(f"{unique_subjects} unique subject IDs found")
            
            # Look for group assignment descriptions
            assignment_patterns = [
                r'(?i)animals?.{0,20}judged.{0,20}to.{0,20}be',
                r'(?i)placed.{0,20}into.{0,20}appropriate',
                r'(?i)stepwise.{0,20}fashion',
                r'(?i)randomized.{0,20}into'
            ]
            
            assignment_count = sum(
                len(re.findall(pattern, content, re.IGNORECASE))
                for pattern in assignment_patterns
            )
            
            if assignment_count >= 1:
                total_score += assignment_count * 3
                evidence_items.append(f"{assignment_count} assignment procedures described")
            
            # Threshold for SE generation
            se_threshold = 20
            confidence = min(90, 50 + (total_score * 2))
            
            logger.info(f"SE domain analysis: score={total_score}, subjects={unique_subjects}, threshold={se_threshold}, confidence={confidence}")
            
            if total_score >= se_threshold and unique_subjects >= 5:
                evidence_text = f"Generated from subject assignments (score: {total_score}, {unique_subjects} subjects): {'; '.join(evidence_items[:3])}"
                return self._create_domain_detection(study, 'SE', confidence, evidence_text)
            else:
                logger.info(f"SE domain not generated: score {total_score} below threshold {se_threshold} or insufficient subjects")
            
            return False
            
        except Exception as e:
            logger.error(f"Error generating SE domain: {e}")
            return False
    
    def _generate_tx_domain(self, study, content: str) -> bool:
        """Generate TX domain from treatment group definitions"""
        try:
            logger.info("Analyzing content for TX domain generation")
            
            # Look for treatment group definition patterns with weights
            tx_indicators = [
                (r'(?i)group.{0,10}\d+.*mg/kg', 4),            # Dose groups with units - HIGH VALUE
                (r'(?i)vehicle.*control', 3),                   # Vehicle control groups
                (r'(?i)dose.{0,20}level', 3),                   # Dose level definitions
                (r'(?i)treatment.{0,20}group', 2),             # Treatment groups
                (r'(?i)formulation.{0,20}concentration', 2),    # Formulation info
                (r'(?i)dose.{0,20}volume', 2),                 # Dosing parameters
                (r'(?i)oral.{0,20}gavage', 2),                 # Administration route
                (r'(?i)mg/kg/day', 1),                         # Dosing units
                (r'(?i)number.{0,20}of.{0,20}animals', 1),    # Group sizes
                (r'(?i)test.{0,20}article', 2),               # Test article info
                (r'(?i)experimental.{0,20}design', 2),        # Design context
                (r'(?i)group.{0,20}organization', 3),         # Group organization
                (r'(?i)justification.{0,20}of.{0,20}dosage', 2), # Dose justification
            ]
            
            # Calculate weighted score
            total_score = 0
            evidence_items = []
            
            for pattern, weight in tx_indicators:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    score = len(matches) * weight
                    total_score += score
                    evidence_items.append(f"{len(matches)} treatment patterns")
                    logger.debug(f"TX pattern '{pattern}': {len(matches)} matches (score: {score})")
            
            # Look for dose values (indicating treatment parameters)
            dose_matches = re.findall(r'\d+\.?\d*\s*mg/kg', content, re.IGNORECASE)
            unique_doses = len(set(dose_matches))
            
            if unique_doses >= 2:  # At least control + one dose level
                total_score += unique_doses * 3
                evidence_items.append(f"{unique_doses} unique dose levels")
            
            # Look for group numbers
            group_matches = re.findall(r'group\s*\d+', content, re.IGNORECASE)
            unique_groups = len(set([match.lower() for match in group_matches]))
            
            if unique_groups >= 2:  # At least 2 groups
                total_score += unique_groups * 2
                evidence_items.append(f"{unique_groups} treatment groups")
            
            # Look for treatment tables or organization sections
            table_patterns = [
                r'(?i)treatment.*table',
                r'(?i)group.*table',
                r'(?i)dose.*table',
                r'(?i)organization.*test.*groups',
                r'(?i)study.*group.*arrangement'
            ]
            
            table_count = sum(
                len(re.findall(pattern, content, re.IGNORECASE))
                for pattern in table_patterns
            )
            
            if table_count >= 1:
                total_score += table_count * 4
                evidence_items.append(f"{table_count} treatment organization tables")
            
            # Threshold for TX generation
            tx_threshold = 25
            confidence = min(95, 60 + (total_score * 1.5))
            
            logger.info(f"TX domain analysis: score={total_score}, doses={unique_doses}, groups={unique_groups}, threshold={tx_threshold}, confidence={confidence}")
            
            if total_score >= tx_threshold and unique_doses >= 2 and unique_groups >= 2:
                evidence_text = f"Generated from treatment definitions (score: {total_score}, {unique_groups} groups, {unique_doses} dose levels): {'; '.join(evidence_items[:3])}"
                return self._create_domain_detection(study, 'TX', confidence, evidence_text)
            else:
                logger.info(f"TX domain not generated: score {total_score} below threshold {tx_threshold} or insufficient groups/doses")
            
            return False
            
        except Exception as e:
            logger.error(f"Error generating TX domain: {e}")
            return False
    
    @transaction.atomic
    def _create_domain_detection(self, study, domain_code: str, confidence: int, evidence: str) -> bool:
        """Create a domain detection record"""
        try:
            # Get domain object
            domain_obj = self.Domain.objects.get(code=domain_code)
            
            # Check if detection already exists
            existing = self.DetectedDomain.objects.filter(
                study=study, domain=domain_obj
            ).first()
            
            if not existing:
                # Create new detection
                detection = self.DetectedDomain.objects.create(
                    study=study,
                    domain=domain_obj,
                    content_id=[],  # No specific content IDs for generated domains
                    page=[],        # No specific pages for generated domains
                    confident_score=confidence
                )
                
                logger.info(f"Created {domain_code} domain detection (ID: {detection.id}, confidence: {confidence}%)")
                logger.info(f"Evidence: {evidence}")
                return True
            else:
                logger.info(f"{domain_code} domain already detected (ID: {existing.id})")
                # Update confidence if new confidence is higher
                if confidence > existing.confident_score:
                    existing.confident_score = confidence
                    existing.save()
                    logger.info(f"Updated {domain_code} confidence to {confidence}%")
                return True
                
        except self.Domain.DoesNotExist:
            logger.error(f"Domain {domain_code} not found in database. Please run: python manage.py load_domains domains.json")
            return False
        except Exception as e:
            logger.error(f"Error creating {domain_code} detection: {e}")
            return False


def enhance_domain_detection(study, study_content_model, detected_domain_model, domain_model, force_regenerate=False):
    """
    Convenience function to enhance domain detection with structural domains
    
    Args:
        study: Study instance
        study_content_model: StudyContent model class
        detected_domain_model: DetectedDomain model class  
        domain_model: Domain model class
        force_regenerate: If True, regenerate domains even if they exist
        
    Returns:
        Dict with generation results
    """
    generator = StructuralDomainGenerator(
        study_content_model, detected_domain_model, domain_model
    )
    return generator.generate_missing_structural_domains(study, force_regenerate)


def test_structural_generation(study):
    """Test function for structural domain generation"""
    try:
        from builder.models import StudyContent, DetectedDomain, Domain
        
        results = enhance_domain_detection(study, StudyContent, DetectedDomain, Domain)
        
        print("Structural Domain Generation Test Results:")
        print("=" * 50)
        for domain, success in results.items():
            status = "✓ Generated/Exists" if success else "✗ Not generated"
            print(f"  {domain}: {status}")
        
        return results
        
    except ImportError as e:
        print(f"Error importing models: {e}")
        return {}
    except Exception as e:
        print(f"Error testing structural generation: {e}")
        return {}


if __name__ == "__main__":
    print("Structural Domain Generator for SEND TE, SE, TX domains")
    print("=" * 60)
    print("This module generates structural domains by analyzing study design patterns.")
    print("\nUsage:")
    print("  from builder.utils.structural_domain_generator import enhance_domain_detection")
    print("  results = enhance_domain_detection(study, StudyContent, DetectedDomain, Domain)")