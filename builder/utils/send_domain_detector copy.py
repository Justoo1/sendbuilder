"""
Improved SEND Domain Detection System

This module provides accurate detection of SEND domains in toxicology studies
by analyzing actual data patterns rather than just keyword matching.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from django.db import transaction, models
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    evidence: List[str]  # What patterns/data were found
    data_type: str  # e.g., 'table', 'listing', 'summary'


class SENDDataValidator:
    """Validates that detected content represents actual SEND domain data"""
    
    # SEND-specific data indicators
    SEND_INDICATORS = {
        'DM': {
            'required_fields': ['USUBJID', 'SUBJID', 'SPECIES', 'STRAIN'],
            'table_headers': ['Subject', 'Animal', 'Demographics'],
            'data_patterns': [
                r'(?i)USUBJID\s*[:\|]\s*\w+',
                r'(?i)Species\s*[:\|]\s*\w+',
                r'(?i)Strain\s*[:\|]\s*\w+',
                r'(?i)Sex\s*[:\|]\s*[MF]'
            ]
        },
        'BW': {
            'required_fields': ['USUBJID', 'BWTEST', 'BWORRES', 'BWORRESU'],
            'table_headers': ['Body Weight', 'Weight', 'BW'],
            'data_patterns': [
                r'(?i)body\s*weight.*\d+\.?\d*\s*(g|kg|lb)',
                r'(?i)BWTEST\s*[:\|]\s*\w+',
                r'(?i)weight.*\d+\.?\d*',
                r'\d+\.?\d*\s*(g|kg|grams?|kilograms?)'
            ]
        },
        'CL': {
            'required_fields': ['USUBJID', 'CLTEST', 'CLORRES'],
            'table_headers': ['Clinical', 'Observation', 'Signs', 'Group Information', 'Animals by Time'],
            'data_patterns': [
                # Core SEND CL patterns (keep existing)
                r'(?i)CLTEST\s*[:\|]\s*\w+',
                r'(?i)clinical\s*observation.*normal|abnormal',
                r'(?i)observation.*\d+.*day',
                r'(?i)(normal|abnormal|not\s*observed)',
                
                # Flexible clinical observation indicators (not too specific)
                r'(?i)clinical\s*observations?',  # Generic clinical observations
                r'(?i)animals?\s*by\s*time',      # Common in clinical obs tables
                r'(?i)group\s*(information|data)', # Group organization
                r'(?i)timeslot\s*(definition|data)', # Time-based observations
                
                # Common dosing context (appears in many studies)
                r'(?i)(control|vehicle|dose)\s*group',
                r'(?i)dose\s*level',
                r'(?i)\d+\s*mg/kg.*group',        # Dose with group context
                
                # Study structure indicators (broad patterns)
                r'(?i)(pre|post)\s*dose',         # Common timing
                r'(?i)(am|pm|\d+\s*min)',         # Time indicators
                r'(?i)(scheduled|unscheduled)',   # Observation types
            ]
        },
        'LB': {
            'required_fields': ['USUBJID', 'LBTEST', 'LBORRES', 'LBORRESU'],
            'table_headers': ['Laboratory', 'Lab', 'Hematology', 'Chemistry'],
            'data_patterns': [
                r'(?i)LBTEST\s*[:\|]\s*\w+',
                r'(?i)(hematology|chemistry|urinalysis)',
                r'(?i)\w+\s*\d+\.?\d*\s*(mg/dL|g/dL|µg/mL|IU/L)',
                r'(?i)(glucose|albumin|creatinine|BUN).*\d+'
            ]
        },
        'MA': {
            'required_fields': ['USUBJID', 'MATEST', 'MAORRES'],
            'table_headers': ['Macroscopic', 'Gross', 'Necropsy'],
            'data_patterns': [
                r'(?i)MATEST\s*[:\|]\s*\w+',
                r'(?i)(macroscopic|gross).*findings?',
                r'(?i)necropsy.*findings?',
                r'(?i)(normal|no\s*abnormalities|within\s*normal)'
            ]
        },
        'MI': {
            'required_fields': ['USUBJID', 'MITEST', 'MIORRES'],
            'table_headers': ['Microscopic', 'Histopathology', 'Histo'],
            'data_patterns': [
                r'(?i)MITEST\s*[:\|]\s*\w+',
                r'(?i)(microscopic|histopatholog)',
                r'(?i)tissue.*examination',
                r'(?i)(minimal|mild|moderate|severe|marked)'
            ]
        },
        'EX': {
            'required_fields': ['USUBJID', 'EXTRT', 'EXDOSE', 'EXDOSU'],
            'table_headers': ['Exposure', 'Dosing', 'Treatment'],
            'data_patterns': [
                r'(?i)EXTRT\s*[:\|]\s*\w+',
                r'(?i)dose.*\d+\.?\d*\s*(mg/kg|µg/kg)',
                r'(?i)(control|vehicle|test\s*article)',
                r'(?i)dosing.*schedule'
            ]
        }
    }
    
    def validate_send_data(self, domain_code: str, content: str, page_num: int) -> Tuple[bool, int, List[str]]:
        """
        Validate that content contains actual SEND domain data
        
        Returns:
            Tuple[bool, int, List[str]]: (is_valid, confidence_score, evidence)
        """
        if domain_code not in self.SEND_INDICATORS:
            return False, 0, []
        
        indicators = self.SEND_INDICATORS[domain_code]
        evidence = []
        confidence = 0
        
        # Check for SEND field patterns
        field_matches = 0
        for pattern in indicators['data_patterns']:
            matches = re.findall(pattern, content)
            if matches:
                field_matches += len(matches)
                evidence.extend([f"Found pattern: {match}" for match in matches[:3]])  # Limit evidence
        
        if field_matches > 0:
            confidence += min(40, field_matches * 10)  # Max 40 points for patterns
        
        # Check for table structure indicators
        table_score = self._check_table_structure(content, indicators['table_headers'])
        confidence += table_score
        evidence.extend(self._get_table_evidence(content, indicators['table_headers']))
        
        # Check for data value patterns (numbers, units, etc.)
        data_score = self._check_data_values(content, domain_code)
        confidence += data_score
        
        # Bonus for multiple data points
        if self._has_multiple_data_points(content):
            confidence += 10
            evidence.append("Multiple data points detected")
        
        # Penalty for just keyword mentions without data
        if confidence < 20 and self._only_keyword_mentions(content, domain_code):
            confidence = max(0, confidence - 15)
            evidence.append("Only keyword mentions, no actual data")
        
        is_valid = confidence >= 30  # Threshold for valid SEND data
        return is_valid, min(100, confidence), evidence
    
    def _check_table_structure(self, content: str, headers: List[str]) -> int:
        """Check for table-like structure with relevant headers"""
        score = 0
        
        # Look for table headers
        for header in headers:
            if re.search(rf'(?i){re.escape(header)}', content):
                score += 10
        
        # Look for tabular data patterns
        lines = content.split('\n')
        tabular_lines = 0
        
        for line in lines:
            # Check for lines with multiple data values separated by tabs/spaces
            if re.search(r'\d+.*\d+.*\d+', line):  # Multiple numbers
                tabular_lines += 1
            elif re.search(r'\w+\s+\w+\s+\w+\s+\w+', line):  # Multiple words (table row)
                tabular_lines += 1
        
        if tabular_lines > 2:  # At least 3 table-like lines
            score += 15
        
        return min(25, score)
    
    def _get_table_evidence(self, content: str, headers: List[str]) -> List[str]:
        """Get evidence of table structure"""
        evidence = []
        for header in headers:
            if re.search(rf'(?i){re.escape(header)}', content):
                evidence.append(f"Found table header: {header}")
        return evidence[:2]  # Limit evidence
    
    def _check_data_values(self, content: str, domain_code: str) -> int:
        """Check for actual data values appropriate to the domain"""
        score = 0
        
        # Domain-specific data value patterns
        value_patterns = {
            'BW': [r'\d+\.?\d*\s*(g|kg)', r'weight.*\d+'],
            'LB': [r'\d+\.?\d*\s*(mg/dL|g/dL|IU/L)', r'(normal|high|low)'],
            'CL': [r'(normal|abnormal|present|absent)', r'day\s*\d+'],
            'EX': [r'\d+\.?\d*\s*(mg/kg|µg/kg)', r'dose.*\d+']
        }
        
        if domain_code in value_patterns:
            for pattern in value_patterns[domain_code]:
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                score += min(15, matches * 5)
        
        return min(30, score)
    
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
    """Main class for SEND domain detection"""
    
    def __init__(self, study_content_model, detected_domain_model, domain_model):
        self.StudyContent = study_content_model
        self.DetectedDomain = detected_domain_model
        self.Domain = domain_model
        self.validator = SENDDataValidator()
        
    def detect_domains_for_study(self, study) -> Dict[str, any]:
        """
        Detect SEND domains for all pages of a study
        
        Args:
            study: Study instance
            
        Returns:
            Dict with detection results
        """
        try:
            # Get all study content pages
            study_pages = self.StudyContent.objects.filter(
                study=study
            ).order_by('page')
            
            if not study_pages.exists():
                return {
                    'success': False,
                    'error': 'No study content found. Please process PDF first.',
                    'detected_domains': []
                }
            
            # Get available domains
            available_domains = self.Domain.objects.all()
            domain_mapping = {d.code: d for d in available_domains}
            
            # Clear existing detections for this study
            self._clear_existing_detections(study)
            
            # Process each page
            detection_results = []
            
            for page in study_pages:
                page_results = self._detect_domains_in_page(
                    page, domain_mapping
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
                'detected_domains': len(saved_detections),
                'summary': summary,
                'detections': saved_detections
            }
            
        except Exception as e:
            logger.error(f"Error detecting domains for study {study.study_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'detected_domains': []
            }
    
    def _detect_domains_in_page(self, study_page, domain_mapping: Dict) -> List[DomainDetectionResult]:
        """Detect domains in a single page"""
        results = []
        content = study_page.content
        
        if not content or len(content.strip()) < 50:  # Skip very short content
            return results
        
        for domain_code, domain_obj in domain_mapping.items():
            # Validate SEND data for this domain
            is_valid, confidence, evidence = self.validator.validate_send_data(
                domain_code, content, study_page.page
            )
            
            if is_valid:  # Only include valid detections
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
                    f"with confidence {confidence}"
                )
        
        return results
    
    def _determine_data_type(self, content: str) -> str:
        """Determine the type of data found"""
        if 'TABLE' in content.upper() or self._looks_like_table(content):
            return 'table'
        elif 'LISTING' in content.upper() or 'LIST' in content.upper():
            return 'listing'
        elif 'SUMMARY' in content.upper():
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
    
    @transaction.atomic
    def _save_detections(self, detection_results: List[DomainDetectionResult]) -> List[Dict]:
        """Save valid detections to database"""
        saved_detections = []
        
        for result in detection_results:
            if not result.detected:
                continue
                
            try:
                # Get domain object
                domain_obj = self.Domain.objects.get(code=result.domain_code)
                
                # Create detection record
                detection = self.DetectedDomain.objects.create(
                    study_id=self._get_study_id_from_content(result.content_id),
                    domain=domain_obj,
                    content_id=[result.content_id],  # Store as list for JSON field
                    page=[result.page_number],  # Store as list for JSON field
                    confident_score=result.confidence_score
                )
                
                saved_detections.append({
                    'id': detection.id,
                    'domain_code': result.domain_code,
                    'domain_name': result.domain_name,
                    'page': result.page_number,
                    'confidence': result.confidence_score,
                    'evidence': result.evidence,
                    'data_type': result.data_type
                })
                
            except Exception as e:
                logger.error(f"Error saving detection for {result.domain_code}: {str(e)}")
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


# Utility functions for easy usage
def detect_domains_for_study(study, study_content_model, detected_domain_model, domain_model):
    """
    Convenience function to detect domains for a study
    
    Args:
        study: Study instance
        study_content_model: StudyContent model class
        detected_domain_model: DetectedDomain model class  
        domain_model: Domain model class
        
    Returns:
        Detection results dictionary
    """
    detector = SENDDomainDetector(
        study_content_model, 
        detected_domain_model, 
        domain_model
    )
    return detector.detect_domains_for_study(study)


def get_detection_summary(study, detected_domain_model):
    """Get summary of existing detections for a study"""
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
    """Re-run domain detection for a study (clears existing first)"""
    return detect_domains_for_study(study, study_content_model, detected_domain_model, domain_model)


# Example usage in Django view
def detect_domains_view_logic(study, request=None):
    """
    Example logic for Django view
    """
    from builder.models import StudyContent, DetectedDomain, Domain  # Replace with actual imports
    
    try:
        result = detect_domains_for_study(
            study=study,
            study_content_model=StudyContent,
            detected_domain_model=DetectedDomain,
            domain_model=Domain
        )
        
        if result['success']:
            message = f"Successfully detected {result['detected_domains']} domains across {result['total_pages']} pages"
            return {
                'success': True,
                'message': message,
                'data': result
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