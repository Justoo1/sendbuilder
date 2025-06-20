# extraction/services.py
from typing import Dict, List, Any
from django.db import transaction
from builder.models import Study, DetectedDomain, ExtractedDomain, FDAFile
from .pipeline import ExtractionPipeline, ExtractionConfig
from .fda_generator import FDAFileGenerator
from .utils import ProgressTracker, ExtractionCache

class ExtractionService:
    """High-level service for managing extractions"""
    
    def __init__(self, study_id: int):
        self.study_id = study_id
        self.study = Study.objects.get(study_id=study_id)
    
    def extract_single_domain(self, domain_code: str, config: ExtractionConfig = None) -> Dict[str, Any]:
        """Extract a single domain with progress tracking"""
        # Set status to in progress
        ExtractionCache.set_extraction_status(self.study_id, domain_code, 'in_progress')
        
        try:
            # Create pipeline
            pipeline = ExtractionPipeline(config or ExtractionConfig())
            
            # Run extraction
            result = pipeline.extract_domain(self.study_id, domain_code)
            
            # Update cache based on result
            if result['success']:
                ExtractionCache.set_extraction_status(self.study_id, domain_code, 'completed')
            else:
                ExtractionCache.set_extraction_status(self.study_id, domain_code, 'failed')
            
            return result
            
        except Exception as e:
            ExtractionCache.set_extraction_status(self.study_id, domain_code, 'failed')
            return {
                'success': False,
                'error': str(e)
            }
    
    def extract_all_domains(self, config: ExtractionConfig = None) -> Dict[str, Any]:
        """Extract all detected domains"""
        detected_domains = DetectedDomain.objects.filter(study_id=self.study_id)
        
        if not detected_domains.exists():
            return {
                'success': False,
                'error': 'No detected domains found'
            }
        
        # Initialize progress tracker
        tracker = ProgressTracker(self.study_id, len(detected_domains))
        
        results = {}
        total_success = 0
        
        for detected_domain in detected_domains:
            domain_code = detected_domain.domain.code
            
            try:
                tracker.update_progress(domain_code, 'in_progress')
                result = self.extract_single_domain(domain_code, config)
                
                results[domain_code] = result
                
                if result['success']:
                    total_success += 1
                    tracker.update_progress(domain_code, 'completed', {
                        'record_count': len(result.get('data', []))
                    })
                else:
                    tracker.update_progress(domain_code, 'failed', {
                        'error': result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                results[domain_code] = {'success': False, 'error': str(e)}
                tracker.update_progress(domain_code, 'failed', {'error': str(e)})
        
        return {
            'success': total_success > 0,
            'total_domains': len(detected_domains),
            'successful_extractions': total_success,
            'results': results
        }
    
    def generate_submission_package(self) -> Dict[str, Any]:
        """Generate complete FDA submission package"""
        try:
            # Check if we have extracted domains
            extracted_domains = ExtractedDomain.objects.filter(study_id=self.study_id)
            
            if not extracted_domains.exists():
                return {
                    'success': False,
                    'error': 'No extracted domains found'
                }
            
            # Generate FDA files
            generator = FDAFileGenerator(self.study_id)
            fda_result = generator.generate_all_files()
            
            if not fda_result['success']:
                return fda_result
            
            # Package summary
            return {
                'success': True,
                'package_info': {
                    'study_id': self.study_id,
                    'domains_extracted': len(extracted_domains),
                    'fda_files_generated': len(fda_result['files_generated']),
                    'generated_files': fda_result['files_generated']
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """Get comprehensive extraction summary"""
        detected_domains = DetectedDomain.objects.filter(study_id=self.study_id)
        extracted_domains = ExtractedDomain.objects.filter(study_id=self.study_id)
        fda_files = FDAFile.objects.filter(study_id=self.study_id)
        
        total_records = sum(
            len(ed.content) if ed.content else 0 
            for ed in extracted_domains
        )
        
        domain_summary = {}
        for dd in detected_domains:
            domain_code = dd.domain.code
            domain_summary[domain_code] = {
                'detected': True,
                'pages': dd.page,
                'extracted': False,
                'record_count': 0
            }
        
        for ed in extracted_domains:
            if ed.domain.code in domain_summary:
                domain_summary[ed.domain.code].update({
                    'extracted': True,
                    'record_count': len(ed.content) if ed.content else 0
                })
        
        return {
            'study_info': {
                'id': self.study_id,
                'title': self.study.title,
                'description': self.study.description
            },
            'summary_stats': {
                'total_detected_domains': len(detected_domains),
                'total_extracted_domains': len(extracted_domains),
                'total_records': total_records,
                'total_fda_files': len(fda_files)
            },
            'domain_details': domain_summary,
            'extraction_progress': len(extracted_domains) / len(detected_domains) * 100 if detected_domains else 0
        }