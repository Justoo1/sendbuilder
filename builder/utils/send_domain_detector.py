"""
Improved SEND Domain Detection System - Integrated with existing patterns

This module integrates your proven patterns.py with the detection logic
while preserving all existing functionality.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from django.db import transaction, models
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import your existing patterns
from .patterns import DOMAIN_PATTERNS
from .send_validation import validate_domain_content
from .structural_domain_generator import StructuralDomainGenerator

logger = logging.getLogger(__name__)


@dataclass
class DomainDetectionResult:
    """Result of domain detection for a specific page"""
    domain_code: str
    domain_name: str
    detected: bool
    confidence_score: int  # 0-100
    page_number: int
    content_id: int
    evidence: List[str]  # What patterns were found
    data_type: str  # e.g., 'table', 'listing', 'summary'


class SENDDataValidator:
    """Validates SEND domain data using your proven patterns"""
    
    def __init__(self):
        # Use your existing patterns directly
        self.domain_patterns = DOMAIN_PATTERNS
    
    def validate_send_data(self, domain_code: str, content: str, page_num: int) -> Tuple[bool, int, List[str]]:
        """
        Validate SEND domain data using proven pattern approach + utility enhancements
        
        Returns:
            Tuple[bool, int, List[str]]: (is_valid, confidence_score, evidence)
        """
        if domain_code not in self.domain_patterns:
            return False, 0, []
        
        domain_info = self.domain_patterns[domain_code]
        patterns = domain_info['patterns']
        evidence = []
        confidence = 0
        
        # Count pattern matches (your proven approach - KEEP THIS)
        pattern_matches = 0
        matched_patterns = []
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                pattern_matches += len(matches)
                matched_patterns.append(pattern)
                evidence.append(f"Found: {domain_info['name']} pattern")
        
        # Simple confidence calculation based on your pattern matching (KEEP THIS)
        if pattern_matches > 0:
            # Start with base confidence, add for each match
            confidence = min(85, 25 + (pattern_matches * 12))
        
        # Bonus for multiple different pattern types (KEEP THIS)
        unique_patterns_matched = len(matched_patterns)
        if unique_patterns_matched >= 2:
            confidence += 15
            evidence.append(f"Multiple pattern types: {unique_patterns_matched}")
        elif unique_patterns_matched >= 3:
            confidence += 25  # Strong evidence
            evidence.append(f"Strong pattern diversity: {unique_patterns_matched}")
        
        # Check for data context (KEEP THIS)
        data_context_score = self._check_data_context(content, domain_code)
        confidence += data_context_score

        if data_context_score > 0:
            evidence.append("Contains relevant data values")

        # Domain-specific bonuses (KEEP THIS)
        domain_bonus = self._get_domain_specific_bonus(domain_code, content)
        confidence += domain_bonus

        if domain_bonus > 10:
            evidence.append(f"Strong {domain_info['name']} indicators")
        
        # Bonus for multiple data points (KEEP THIS)
        if self._has_multiple_data_points(content):
            confidence += 10
            evidence.append("Multiple data points detected")

        # REPLACE the domain-specific validation section with utility call
        # Remove the old VS-specific validation code and replace with:
        
        # Apply domain-specific validation using utility functions
        confidence, evidence = validate_domain_content(
            domain_code, 
            content, 
            confidence, 
            evidence
        )
        
        # Keep your existing final checks
        # Penalty for just keyword mentions without data
        if confidence < 25 and self._only_keyword_mentions(content, domain_code):
            confidence = max(0, confidence - 10)
            evidence.append("Mostly keyword mentions, limited actual data")
        
        is_valid = confidence >= 30  # Threshold for valid SEND data
        return is_valid, min(100, confidence), evidence
    
    def _check_data_context(self, content: str, domain_code: str) -> int:
        """Check for data context relevant to the domain"""
        score = 0
        
        # Domain-specific data indicators with stricter validation
        data_indicators = {
            'BW': [
                r'\d+\.?\d*\s*(g|kg)', r'weight.*\d+',
                r'body.{0,10}weight.{0,10}\(grams\)',
                r'\d+\.\d+\s*g'
            ],
            'LB': [r'\d+\.?\d*\s*(mg/dL|g/dL|IU/L)', r'(normal|high|low|elevated)'],
            'CL': [
                r'(normal|abnormal|present|absent)', r'day\s*\d+', r'group\s*\d+',
                r'activity.*hypoactive', r'salivation', r'squinting', r'staining'
            ],
            'EX': [
                r'\d+\.?\d*\s*(mg/kg|µg/kg)', r'dose.*\d+', r'(control|vehicle)', 
                r'intravenous.{0,10}injection', r'dose.{0,10}level'
            ],
            'MA': [
                r'(normal|abnormal|unremarkable)', r'organ.*\w+',
                r'no.{0,5}visible.{0,5}lesions', r'lesions', r'enlarged', r'discoloration'
            ],
            'MI': [r'(minimal|mild|moderate|severe)', r'tissue.*\w+'],
            'OM': [r'\d+\.?\d*\s*(g|mg)', r'organ.*weight'],
            'FW': [
                r'\d+\.?\d*\s*(g|ml)', r'consumption.*\d+',
                r'food.{0,10}consumption', r'daily.{0,10}food',
                r'daily.{0,10}food.{0,10}cons', r'food.{0,10}cons.{0,10}per.{0,10}animal'  # Added missing patterns
            ],
            'VS': [
                # Removed 'respiration' pattern that was causing false positives
                r'\d+\.?\d*\s*(bpm|°C|mmHg)', r'temperature.*\d+', 
                r'vital.{0,10}signs.*\d+', r'heart.{0,10}rate.*\d+'  # More specific patterns
            ],
            'DD': [r'(euthanized|died|found dead)', r'cause.*death'],
            'DS': [
                r'(terminal|sacrifice|mortality)', r'disposition.*\w+',
                r'killed.{0,10}terminal', r'found.{0,10}dead', r'euthanized'
            ],
            'CV': [r'\d+\.?\d*\s*(mmHg|bpm)', r'blood.*pressure'],
            'EG': [r'(ECG|QT.*interval)', r'heart.*rate.*\d+'],
            'PA': [r'(palpable|mass|tumor)', r'palpation.*\w+'],
            'PM': [r'\d+\.?\d*\s*(cm|mm)', r'length.*\d+'],
            'PC': [r'\d+\.?\d*\s*(ng/mL|µg/mL)', r'concentration.*\d+'],
            'PP': [r'(AUC|Cmax|half.*life)', r'PK.*parameter'],
            'TS': [
                r'objective', r'study.{0,10}schedule', r'experimental.{0,10}design'
            ],
            'TX': [
                r'group.{0,10}\d+', r'dose.{0,10}level', r'treatment.{0,10}group'
            ],
            'CO': [
                r'(?i)comment:\s*\w+',                    # "Comment: [text]"
                r'(?i)note:\s*\w+',                       # "Note: [text]" 
                r'(?i)remarks?:\s*\w+',                   # "Remarks: [text]"
                r'(?i)explanation:\s*\w+',                # "Explanation: [text]"
                r'(?i)rationale:\s*\w+',                  # "Rationale: [text]"
                r'(?i)additional\s+information:\s*\w+',   # "Additional Information: [text]"
                r'(?i)protocol\s+deviation:\s*\w+',       # "Protocol Deviation: [text]"
                r'(?i)investigator\s+comment:\s*\w+',     # "Investigator Comment: [text]"
                r'(?i)sponsor\s+comment:\s*\w+',          # "Sponsor Comment: [text]"
                r'(?i)data\s+clarification:\s*\w+',       # "Data Clarification: [text]"
                r'(?i)comment\s+field:\s*\w+',            # "Comment Field: [text]"
                r'(?i)see\s+attached',                    # "See attached" - common in comments
                r'(?i)as\s+noted',                        # "As noted" - common phrase
                r'(?i)please\s+refer',                    # "Please refer" - common phrase
                r'(?i)^\s*\*\s*\w+',                      # Lines starting with asterisk (footnotes)
                r'(?i)^\s*note\s*\d*:\s*\w+',            # "Note 1:", "Note 2:", etc.
            ],
        }
        
        if domain_code in data_indicators:
            for pattern in data_indicators[domain_code]:
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                score += min(10, matches * 3)
        
        # Add domain-specific context validation to prevent false positives
        if domain_code == 'VS':
            # VS should only match if we have actual vital sign measurements, not clinical observations
            if re.search(r'clinical.{0,20}observ', content, re.IGNORECASE):
                score = max(0, score - 15)  # Penalty for being in clinical observations context
        
        # General data presence
        numbers_count = len(re.findall(r'\d+\.?\d*', content))
        if numbers_count > 5:
            score += 5
        
        return min(20, score)
    
    def _get_domain_specific_bonus(self, domain_code: str, content: str) -> int:
        """Get domain-specific bonus scoring"""
        bonus = 0
        
        # Domain-specific strong indicators
        strong_indicators = {
            'CL': [
                r'(?i)clinical\s*observations?\s*-?\s*animals?\s*by\s*time',
                r'(?i)group\s*information.*timeslot',
                r'(?i)observation.*period.*day'
            ],
            'BW': [
                r'(?i)individual.{0,20}body.{0,20}weight',
                r'(?i)summary.{0,20}body.{0,20}weight',
                r'(?i)body.{0,20}weight.*table'
            ],
            'DM': [r'sprague.{0,10}dawley',r'species',r'strain',r'male.*female'],
            'LB': [
                r'(?i)clinical.{0,20}pathology',
                r'(?i)laboratory.{0,20}results.*table',
                r'(?i)(hematology|chemistry).*table'
            ],
            'EX': [
                r'(?i)dose.*administration',
                r'(?i)treatment.*groups?.*mg/kg',
                r'(?i)dosing.*schedule'
            ]
        }
        
        if domain_code in strong_indicators:
            for pattern in strong_indicators[domain_code]:
                if re.search(pattern, content, re.IGNORECASE):
                    bonus += 12
        
        return min(25, bonus)
    
    def _has_multiple_data_points(self, content: str) -> bool:
        """Check if content has multiple data points (indicating a dataset)"""
        # Count lines with numerical data
        lines_with_numbers = len(re.findall(r'^.*\d+.*$', content, re.MULTILINE))
        return lines_with_numbers >= 3
    
    def _only_keyword_mentions(self, content: str, domain_code: str) -> bool:
        """Check if content only mentions keywords without actual data"""
        # Count actual data patterns vs keyword mentions
        data_patterns = len(re.findall(r'\d+\.?\d*', content))
        keyword_count = len(re.findall(rf'(?i){domain_code}', content))
        
        return keyword_count > 0 and data_patterns < 2


class SENDDomainDetector:
    """Main class for SEND domain detection using your patterns"""
    
    def __init__(self, study_content_model, detected_domain_model, domain_model):
        self.StudyContent = study_content_model
        self.DetectedDomain = detected_domain_model
        self.Domain = domain_model
        self.validator = SENDDataValidator()
        self.structural_generator = StructuralDomainGenerator(
            study_content_model, detected_domain_model, domain_model
        )
        
    def detect_domains_for_study(self, study, options=None) -> Dict[str, any]:
        """
        Detect SEND domains for all pages of a study using your patterns
        
        Args:
            study: Study instance
            options: Detection options (deep_analysis, extract_tables, strict_validation)
            
        Returns:
            Dict with detection results
        """
        options = options or {}
        strict_validation = options.get('strict_validation', False)
        confidence_threshold = 70 if strict_validation else 30
        
        try:
            # Get all study content pages
            study_pages = self.StudyContent.objects.filter(
                study=study
            ).order_by('page')
            
            if not study_pages.exists():
                return {
                    'success': False,
                    'error': 'No study content found. Please process PDF first.',
                    'detected_domains': [],
                    'total_pages': 0,
                    'summary': {}
                }
            
            # Get available domains (only those in your patterns)
            available_domains = self.Domain.objects.filter(
                code__in=self.validator.domain_patterns.keys()
            )
            domain_mapping = {d.code: d for d in available_domains}
            print("-"*100)
            print(f"Available domains: {domain_mapping.keys()}")
            print("-"*100)
            
            # Clear existing detections for this study
            self._clear_existing_detections(study)
            
            # Process each page using your patterns
            detection_results = []
            
            for page in study_pages:
                page_results = self._detect_domains_in_page(
                    page, domain_mapping, confidence_threshold
                )
                detection_results.extend(page_results)
            
            # Save valid detections
            saved_detections = self._save_detections(detection_results)
            
            # Compile summary
            summary = self._compile_detection_summary(detection_results, saved_detections)
            
            return {
                'success': True,
                'study_id': study.study_id,
                'total_pages': study_pages.count(),
                'detected_domains': len(set(d['domain_code'] for d in saved_detections)),
                'summary': summary,
                'detections': saved_detections
            }
            
        except Exception as e:
            logger.error(f"Error detecting domains for study {study.study_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'detected_domains': [],
                'total_pages': 0,
                'summary': {}
            }
    
    def _detect_domains_in_page(self, study_page, domain_mapping: Dict, confidence_threshold: int) -> List[DomainDetectionResult]:
        """Detect domains in a single page using your patterns"""
        results = []
        content = study_page.content
        
        if not content or len(content.strip()) < 50:  # Skip very short content
            return results
        
        for domain_code, domain_obj in domain_mapping.items():
            # Use your patterns for validation
            is_valid, confidence, evidence = self.validator.validate_send_data(
                domain_code, content, study_page.page
            )
            
            if is_valid and confidence >= confidence_threshold:
                result = DomainDetectionResult(
                    domain_code=domain_code,
                    domain_name=domain_obj.name,
                    detected=True,
                    confidence_score=confidence,
                    page_number=study_page.page,
                    content_id=study_page.id,
                    evidence=evidence,
                    data_type=self._determine_data_type(content)
                )
                results.append(result)
                
                logger.info(
                    f"Detected {domain_code} on page {study_page.page} "
                    f"with confidence {confidence}%"
                )
        
        return results
    
    def _determine_data_type(self, content: str) -> str:
        """Determine the type of data found"""
        content_upper = content.upper()
        if 'TABLE' in content_upper or self._looks_like_table(content):
            return 'table'
        elif 'LISTING' in content_upper or 'LIST' in content_upper:
            return 'listing'  
        elif 'SUMMARY' in content_upper:
            return 'summary'
        else:
            return 'mixed'
    
    def _looks_like_table(self, content: str) -> bool:
        """Check if content looks like a table"""
        lines = content.split('\n')
        tabular_lines = sum(1 for line in lines if line.count('\t') > 2 or 
                           len(re.findall(r'\s{2,}', line)) > 2)
        return tabular_lines > 3
    
    def _clear_existing_detections(self, study):
        """Clear existing detections for a study"""
        deleted_count = self.DetectedDomain.objects.filter(study=study).count()
        if deleted_count > 0:
            self.DetectedDomain.objects.filter(study=study).delete()
            logger.info(f"Cleared {deleted_count} existing detections for study {study.study_id}")
        else:
            logger.info(f"No existing detections found for study {study.study_id}")
    
    @transaction.atomic
    def _save_detections(self, detection_results: List[DomainDetectionResult]) -> List[Dict]:
        """Save valid detections to database - consolidate by domain"""
        saved_detections = []
        
        if not detection_results:
            return saved_detections
        
        # Group detection results by domain
        domain_groups = {}
        for result in detection_results:
            if not result.detected:
                continue
                
            domain_code = result.domain_code
            if domain_code not in domain_groups:
                domain_groups[domain_code] = {
                    'domain_name': result.domain_name,
                    'content_ids': [],
                    'pages': [],
                    'confidences': [],
                    'evidence': [],
                    'data_types': []
                }
            
            # Accumulate data for this domain
            domain_groups[domain_code]['content_ids'].append(result.content_id)
            domain_groups[domain_code]['pages'].append(result.page_number)
            domain_groups[domain_code]['confidences'].append(result.confidence_score)
            domain_groups[domain_code]['evidence'].extend(result.evidence)
            domain_groups[domain_code]['data_types'].append(result.data_type)
        
        # Save or update one DetectedDomain per domain
        study_id = self._get_study_id_from_content(detection_results[0].content_id)
        
        for domain_code, domain_data in domain_groups.items():
            try:
                # Get domain object
                domain_obj = self.Domain.objects.get(code=domain_code)
                
                # Check if detection already exists for this study and domain
                existing_detection = self.DetectedDomain.objects.filter(
                    study_id=study_id,
                    domain=domain_obj
                ).first()
                
                # Calculate average confidence score
                avg_confidence = sum(domain_data['confidences']) / len(domain_data['confidences'])
                
                if existing_detection:
                    # Update existing detection - append new pages and content_ids
                    existing_content_ids = existing_detection.content_id or []
                    existing_pages = existing_detection.page or []
                    
                    # Merge and deduplicate
                    updated_content_ids = list(set(existing_content_ids + domain_data['content_ids']))
                    updated_pages = list(set(existing_pages + domain_data['pages']))
                    
                    existing_detection.content_id = updated_content_ids
                    existing_detection.page = sorted(updated_pages)  # Keep pages sorted
                    existing_detection.confident_score = int(avg_confidence)
                    existing_detection.save()
                    
                    detection_id = existing_detection.id
                    logger.info(f"Updated {domain_code} detection with {len(domain_data['pages'])} new pages")
                    
                else:
                    # Create new detection record
                    detection = self.DetectedDomain.objects.create(
                        study_id=study_id,
                        domain=domain_obj,
                        content_id=domain_data['content_ids'],
                        page=sorted(domain_data['pages']),  # Keep pages sorted
                        confident_score=int(avg_confidence)
                    )
                    
                    detection_id = detection.id
                    logger.info(f"Created new {domain_code} detection with {len(domain_data['pages'])} pages")
                
                # Add to saved detections for return
                saved_detections.append({
                    'id': detection_id,
                    'domain_code': domain_code,
                    'domain_name': domain_data['domain_name'],
                    'pages': sorted(domain_data['pages']),  # Return all pages
                    'page_count': len(domain_data['pages']),
                    'confidence': int(avg_confidence),
                    'evidence': list(set(domain_data['evidence'])),  # Deduplicate evidence
                    'data_types': list(set(domain_data['data_types']))  # Unique data types
                })
                
            except Exception as e:
                logger.error(f"Error saving detection for {domain_code}: {str(e)}")
                continue
        
        return saved_detections
    
    def _get_study_id_from_content(self, content_id: int) -> int:
        """Get study ID from content ID"""
        try:
            content = self.StudyContent.objects.get(id=content_id)
            return content.study.study_id
        except self.StudyContent.DoesNotExist:
            raise ValueError(f"StudyContent with ID {content_id} not found")
    
    def _compile_detection_summary(self, all_results: List[DomainDetectionResult], 
                                 saved_detections: List[Dict]) -> Dict:
        """Compile detection summary statistics"""
        return {
            'total_detections_found': len(all_results),
            'valid_detections_saved': len(saved_detections),
            'domains_by_confidence': self._group_by_confidence(saved_detections),
            'pages_with_data': len(set(r.page_number for r in all_results if r.detected)),
            'data_types_found': list(set(r.data_type for r in all_results if r.detected))
        }
    
    def _group_by_confidence(self, detections: List[Dict]) -> Dict:
        """Group detections by confidence level"""
        groups = {'high': 0, 'medium': 0, 'low': 0}
        
        for detection in detections:
            confidence = detection['confidence']
            if confidence >= 70:
                groups['high'] += 1
            elif confidence >= 50:
                groups['medium'] += 1
            else:
                groups['low'] += 1
        
        return groups

    def detect_domains_with_structural_generation(self, study, options=None) -> Dict[str, any]:
        """
        Enhanced detection that includes structural domain generation
        """
        
        normal_results = self.detect_domains_for_study(
            study, options
        )
        
        if not normal_results['success']:
            return normal_results
        
        # Get currently detected domains
        detected_codes = [d['domain_code'] for d in normal_results.get('detections', [])]
        
        # Check for missing structural domains and generate them
        missing_structural = []
        structural_domains = ['TE', 'SE', 'TX']
        
        for domain_code in structural_domains:
            if domain_code not in detected_codes:
                missing_structural.append(domain_code)
        
        # Generate missing structural domains
        if missing_structural:
            print(f"Attempting to generate missing structural domains: {missing_structural}")
            generation_results = self.structural_generator.generate_missing_structural_domains(study)
            
            # Update results with generated domains
            for domain_code, generated in generation_results.items():
                if generated and domain_code in missing_structural:
                    # Add to detected domains list
                    domain_obj = self.Domain.objects.get(code=domain_code)
                    normal_results['detections'].append({
                        'id': None,  # Will be set when saved
                        'domain_code': domain_code,
                        'domain_name': domain_obj.name,
                        'pages': [],
                        'page_count': 0,
                        'confidence': 85,
                        'evidence': ['Generated from study structure'],
                        'data_types': ['generated']
                    })
                    normal_results['detected_domains'] += 1
        
        # Update summary
        normal_results['summary']['generated_domains'] = len([
            d for d in normal_results['detections'] if 'generated' in d.get('data_types', [])
        ])
        
        return normal_results

# Utility functions for easy usage (PRESERVED FROM ORIGINAL)
def detect_domains_for_study(study, study_content_model, detected_domain_model, domain_model, options=None):
    """
    Convenience function to detect domains for a study using your patterns
    
    Args:
        study: Study instance
        study_content_model: StudyContent model class
        detected_domain_model: DetectedDomain model class  
        domain_model: Domain model class
        options: Detection options dict
        
    Returns:
        Detection results dictionary
    """
    detector = SENDDomainDetector(
        study_content_model, 
        detected_domain_model, 
        domain_model
    )
    # return detector.detect_domains_for_study(study, options)
    return detector.detect_domains_with_structural_generation(study, options)


def get_detection_summary(study, detected_domain_model):
    """Get summary of existing detections for a study (PRESERVED FROM ORIGINAL)"""
    detections = detected_domain_model.objects.filter(study=study).select_related('domain')
    
    return {
        'total_detections': detections.count(),
        'domains_detected': list(detections.values_list('domain__code', flat=True).distinct()),
        'average_confidence': detections.aggregate(avg_conf=models.Avg('confident_score'))['avg_conf'] or 0,
        'pages_with_detections': len(set(
            page for detection in detections 
            for page in detection.page
        ))
    }


def redetect_domains_for_study(study, study_content_model, detected_domain_model, domain_model):
    """Re-run domain detection for a study (clears existing first) (PRESERVED FROM ORIGINAL)"""
    return detect_domains_for_study(study, study_content_model, detected_domain_model, domain_model)


def detect_domains_view_logic(study, request=None):
    """
    Updated view logic using your patterns (ENHANCED FROM ORIGINAL)
    """
    from builder.models import StudyContent, DetectedDomain, Domain  # Replace with actual imports
    
    try:
        # Get options from request if available
        options = {}
        if request and request.method == 'POST':
            options = {
                'deep_analysis': request.POST.get('deep_analysis') == 'on',
                'extract_tables': request.POST.get('extract_tables') == 'on', 
                'strict_validation': request.POST.get('strict_validation') == 'on',
            }
        
        result = detect_domains_for_study(
            study=study,
            study_content_model=StudyContent,
            detected_domain_model=DetectedDomain,
            domain_model=Domain,
            options=options
        )
        
        if result['success']:
            message = f"Successfully detected {result['detected_domains']} domains across {result['total_pages']} pages"
            return {
                'success': True,
                'message': message,
                'documents_processed': result['total_pages'],
                'domains_detected': result['detected_domains'],
                'detected_domains': list(set(d['domain_code'] for d in result['detections'])),
                'summary': result['summary'],
                'detections_detail': result.get('detections', []),
                'processing_time': 'N/A',
                'data': result  # Keep original data structure for backward compatibility
            }
        else:
            return {
                'success': False,
                'error': result['error']
            }
            
    except Exception as e:
        logger.error(f"Error in detect_domains_view_logic: {str(e)}")
        return {
            'success': False,
            'error': f"Detection failed: {str(e)}"
        }