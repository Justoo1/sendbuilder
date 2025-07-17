import logging
import zipfile
import io
import pandas as pd
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.urls import reverse_lazy
from django.conf import settings
from django.shortcuts import render
# from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

import json
import threading
from datetime import datetime

from builder.models import Domain, Study, StudyContent, DetectedDomain, ExtractedDomain, FDAFile
from ai.models import AIModel
from builder.forms import StudyUploadForm
from .utils.pdf_processor import process_study_pdf
from .utils.send_domain_detector import detect_domains_for_study, get_detection_summary
from .utils.extractions.pipeline import ExtractionPipeline, ExtractionConfig
from .utils.extractions.fda_generator import FDAFileGenerator
from .utils.ai_model.config import ai_config


logger = logging.getLogger(__name__)


def home(request):
    domains = Domain.objects.all()
    studies = Study.objects.all()
    ai_models = AIModel.objects.all()
    context = {
        'domains': domains,
        'studies': studies,
        'ai_models': ai_models,
        'total_studies': studies.count(),
        'completed_studies': studies.filter(status='completed').count(),
        'in_progress_studies': studies.filter(status='in_progress').count(),
        'total_ai_models': ai_models.count(),
    }
    return render(request, 'builder/home.html', context)

class StudyUploadView(CreateView):
    """View for uploading new studies"""
    model = Study
    form_class = StudyUploadForm
    template_name = 'builder/upload.html'
    
    def get_success_url(self):
        return reverse_lazy('builder:detect_domain', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Try to analyze the uploaded PDF
        try:
            result = process_study_pdf(self.object, StudyContent)
            if result['success']:
                messages.success(
                    self.request, 
                    f'Study "{self.object.title}" uploaded successfully! '
                    'Please go to the next step to detect the domains.'
                )
            else:
                messages.error(self.request, f"PDF analysis failed: {result['error']}")
        except Exception as e:
            logger.warning(f"PDF analysis failed for {self.object.study_id}: {e}")
            messages.success(
                self.request, 
                f'Study "{self.object.title}" uploaded successfully!'
            )
        
        return response


@login_required
def detect_domain(request, pk):
    """
    Main view for domain detection page
    """
    study = get_object_or_404(Study, pk=pk)
    
    # Check if study has content to analyze
    content_count = StudyContent.objects.filter(study=study).count()
    
    # Get existing detection summary if any
    existing_detections = DetectedDomain.objects.filter(study=study).count()

    print("*"*20)
    print(study)
    print("*"*20)
    
    context = {
        'study': study,
        'content_count': content_count,
        'existing_detections': existing_detections,
        'has_content': content_count > 0,
    }
    
    # Handle AJAX POST request for detection
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return handle_detection_request(request, study)
    
    return render(request, 'builder/detect_domain.html', context)


def handle_detection_request(request, study):
    """
    Handle AJAX request for domain detection
    """
    try:
        # Check if study has content
        if not StudyContent.objects.filter(study=study).exists():
            return JsonResponse({
                'success': False,
                'error': 'No study content found. Please upload and process a PDF first.'
            })
        
        # Get detection options from request
        deep_analysis = request.POST.get('deep_analysis') == 'on'
        extract_tables = request.POST.get('extract_tables') == 'on'
        
        # Run detection
        with transaction.atomic():
            result = detect_domains_for_study(
                study=study,
                study_content_model=StudyContent,
                detected_domain_model=DetectedDomain,
                domain_model=Domain
            )
        
        if result['success']:
            # Prepare response data
            response_data = {
                'success': True,
                'documents_processed': result['total_pages'],
                'domains_detected': result['detected_domains'],
                'processing_time': '2.3 seconds',  # You can add actual timing
                'detected_domains': [d['domain_code'] for d in result['detections']],
                'detections_detail': result['detections'],
                'summary': result['summary']
            }
            
            # Log successful detection
            logger.info(
                f"Domain detection completed for study {study.study_id}: "
                f"{result['detected_domains']} domains detected"
            )
            
            return JsonResponse(response_data)
        
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            })
            
    except Exception as e:
        logger.error(f"Error in domain detection for study {study.study_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Detection failed: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def detection_status(request, pk):
    """
    Get current detection status for a study
    """
    study = get_object_or_404(Study, pk=pk)
    
    try:
        summary = get_detection_summary(study, DetectedDomain)
        
        return JsonResponse({
            'success': True,
            'study_id': study.study_id,
            'summary': summary
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def redetect_domains(request, pk):
    """
    Re-run domain detection for a study
    """
    study = get_object_or_404(Study, pk=pk)
    
    try:
        # Clear existing detections and re-run
        with transaction.atomic():
            result = detect_domains_for_study(
                study=study,
                study_content_model=StudyContent,
                detected_domain_model=DetectedDomain,
                domain_model=Domain
            )
        
        if result['success']:
            messages.success(
                request, 
                f"Re-detection completed: {result['detected_domains']} domains detected"
            )
            return JsonResponse({
                'success': True,
                'message': 'Re-detection completed successfully',
                'data': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            })
            
    except Exception as e:
        logger.error(f"Error in re-detection for study {study.study_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Re-detection failed: {str(e)}'
        })


@login_required
def detection_results(request, pk):
    """
    View detailed detection results for a study
    """
    study = get_object_or_404(Study, pk=pk)
    
    # Get all detections with related data
    detections = DetectedDomain.objects.filter(study=study).select_related('domain')
    
    # Group detections by domain
    detection_data = []
    for detection in detections:
        detection_data.append({
            'domain_code': detection.domain.code,
            'domain_name': detection.domain.name,
            'pages': detection.page,
            'confidence': detection.confident_score,
            'content_ids': detection.content_id,
            'created_at': detection.created_at
        })
    
    context = {
        'study': study,
        'detections': detection_data,
        'total_detections': len(detection_data),
        'summary': get_detection_summary(study, DetectedDomain)
    }
    
    return render(request, 'builder/detection_results.html', context)


@login_required
def detection_detail(request, pk, detection_id):
    """
    View details of a specific detection
    """
    study = get_object_or_404(Study, pk=pk)
    detection = get_object_or_404(DetectedDomain, id=detection_id, study=study)
    
    # Get the content pages for this detection
    content_pages = []
    for content_id in detection.content_id:
        try:
            content = StudyContent.objects.get(id=content_id)
            content_pages.append({
                'id': content.id,
                'page': content.page,
                'content_preview': content.content[:500] + '...' if len(content.content) > 500 else content.content
            })
        except StudyContent.DoesNotExist:
            continue
    
    context = {
        'study': study,
        'detection': detection,
        'content_pages': content_pages,
        'domain_name': detection.domain.name
    }
    
    return render(request, 'builder/detection_detail.html', context)


# Utility view functions
def get_study_detection_stats(study):
    """Get detection statistics for a study"""
    detections = DetectedDomain.objects.filter(study=study)
    
    if not detections.exists():
        return {
            'total_detections': 0,
            'domains_detected': [],
            'confidence_distribution': {},
            'pages_analyzed': 0
        }
    
    # Calculate statistics
    domain_codes = list(detections.values_list('domain__code', flat=True))
    confidences = list(detections.values_list('confident_score', flat=True))
    
    # Confidence distribution
    confidence_ranges = {
        'high': len([c for c in confidences if c >= 70]),
        'medium': len([c for c in confidences if 50 <= c < 70]),
        'low': len([c for c in confidences if c < 50])
    }
    
    # Unique pages with detections
    all_pages = set()
    for detection in detections:
        all_pages.update(detection.page)
    
    return {
        'total_detections': detections.count(),
        'domains_detected': list(set(domain_codes)),
        'confidence_distribution': confidence_ranges,
        'pages_analyzed': len(all_pages),
        'average_confidence': sum(confidences) / len(confidences) if confidences else 0
    }


# Extration functions
class ExtractionDashboardView(View):
    """Main dashboard for viewing detected domains and starting extractions"""
    
    def get(self, request, study_id):
        study = get_object_or_404(Study, study_id=study_id)
        detected_domains = DetectedDomain.objects.filter(study=study).select_related('domain')
        extracted_domains = ExtractedDomain.objects.filter(study=study).select_related('domain')
        
        # Create a combined view of domain status
        domain_status = {}
        for dd in detected_domains:
            domain_status[dd.domain.code] = {
                'domain': dd.domain,
                'detected': True,
                'pages': dd.page,
                'extracted': False,
                'record_count': 0,
                'extraction_date': None
            }
        
        for ed in extracted_domains:
            if ed.domain.code in domain_status:
                domain_status[ed.domain.code].update({
                    'extracted': True,
                    'record_count': len(ed.content) if ed.content else 0,
                    'extraction_date': ed.created_at if hasattr(ed, 'created_at') else None
                })
        
        # Get AI model configuration
        model_config = ai_config.get_model_config('CHAT')
        
        context = {
            'study': study,
            'domain_status': domain_status,
            'model_config': model_config,
            'total_detected': len(detected_domains),
            'total_extracted': len(extracted_domains)
        }
        
        return render(request, 'extraction/dashboard.html', context)

class StartExtractionView(View):
    """Start extraction for a specific domain"""

    # Add this method to StartExtractionView class
    def _debug_database_access(self, study_id: int, domain_code: str):
        """Debug database access"""
        logger.debug("=== DATABASE DEBUG START ===")
        
        try:
            # Check if study exists
            study = Study.objects.get(study_id=study_id)
            logger.debug(f"Study found: {study.study_id} - {study.title}")
            
            # Check detected domains
            detected_domains = DetectedDomain.objects.filter(study_id=study_id)
            logger.debug(f"Detected domains count: {detected_domains.count()}")
            
            for dd in detected_domains:
                logger.debug(f"- Domain: {dd.domain.code}, Pages: {dd.page}")
            
            # Check specific domain
            try:
                detected_domain = DetectedDomain.objects.get(
                    study_id=study_id, 
                    domain__code=domain_code
                )
                logger.debug(f"Target domain found: {detected_domain.domain.code}")
            except DetectedDomain.DoesNotExist:
                logger.error(f"Target domain {domain_code} NOT FOUND")
            
        except Exception as e:
            logger.error(f"Database debug error: {e}")
        
        logger.debug("=== DATABASE DEBUG END ===")
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, study_id):
        logger.debug(f"StartExtractionView.post called with study_id={study_id}")
        logger.debug(f"Request body: {request.body}")
        try:
            data = json.loads(request.body)
            domain_code = data.get('domain_code')
            self._debug_database_access(study_id, domain_code)
            
            logger.debug(f"Parsed domain_code: {domain_code}")
            
            if not domain_code:
                logger.debug("No domain_code provided in request")
                return JsonResponse({'error': 'Domain code is required'}, status=400)
            
            # Verify domain exists and is detected
            logger.debug(f"Looking for DetectedDomain with study_id={study_id}, domain__code={domain_code}")
            
            try:
                detected_domain = DetectedDomain.objects.get(
                    study_id=study_id, 
                    domain__code=domain_code
                )
                logger.debug(f"Found detected domain: {detected_domain.id}")
            except DetectedDomain.DoesNotExist:
                logger.error(f"DetectedDomain not found for study_id={study_id}, domain_code={domain_code}")
                return JsonResponse({'error': f'Domain {domain_code} not detected for study {study_id}'}, status=404)
            
            logger.debug(f"Starting background thread for extraction")
            
            # Start extraction in background thread
            thread = threading.Thread(
                target=self._run_extraction,
                args=(study_id, domain_code, request.user.id if request.user.is_authenticated else None)
            )
            thread.daemon = True
            thread.start()
            
            logger.debug(f"Background thread started successfully")
            
            return JsonResponse({
                'message': f'Extraction started for {domain_code} domain',
                'status': 'started'
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error starting extraction: {e}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)
    def _run_extraction(self, study_id: int, domain_code: str, user_id: int = None):
        """Run extraction in background thread"""
        logger.debug(f"_run_extraction thread started for study_id={study_id}, domain_code={domain_code}")
        
        try:
            logger.debug(f"Creating ExtractionConfig")
            
            # Create extraction pipeline
            config = ExtractionConfig(
                chunk_size=4000,
                max_retries=2,
                validate_results=True
            )
            
            logger.debug(f"Creating ExtractionPipeline with config: {config}")
            pipeline = ExtractionPipeline(config)
            
            logger.debug(f"About to call pipeline.extract_domain({study_id}, {domain_code})")
            
            # Run extraction
            result = pipeline.extract_domain(study_id, domain_code)
            
            logger.debug(f"Pipeline.extract_domain returned: {result}")
            
            if result['success']:
                logger.info(f"Extraction completed for {domain_code}: {len(result.get('data', []))} records")
            else:
                logger.error(f"Extraction failed for {domain_code}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Background extraction failed: {e}", exc_info=True)
class ExtractionStatusView(View):
    """Get extraction status for AJAX polling"""
    
    def get(self, request, study_id, domain_code):
        try:
            # Check if extraction exists
            try:
                extracted_domain = ExtractedDomain.objects.get(
                    study_id=study_id,
                    domain__code=domain_code
                )
                
                return JsonResponse({
                    'status': 'completed',
                    'record_count': len(extracted_domain.content) if extracted_domain.content else 0,
                    'has_xpt_file': bool(extracted_domain.xpt_file),
                    'extraction_date': extracted_domain.created_at.isoformat() if hasattr(extracted_domain, 'created_at') else None
                })
                
            except ExtractedDomain.DoesNotExist:
                # Check if extraction is in progress (you might want to implement a status table)
                return JsonResponse({
                    'status': 'not_started'
                })
                
        except Exception as e:
            logger.error(f"Error checking extraction status: {e}")
            return JsonResponse({'error': str(e)}, status=500)

class GenerateFDAFilesView(View):
    """Generate all FDA-required files for the study"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, study_id):
        try:
            study = get_object_or_404(Study, study_id=study_id)
            
            # Check if we have extracted domains
            extracted_domains = ExtractedDomain.objects.filter(study_id=study_id)
            if not extracted_domains.exists():
                return JsonResponse({
                    'error': 'No extracted domains found. Please extract domain data first.'
                }, status=400)
            
            # Generate FDA files
            generator = FDAFileGenerator(study_id)
            result = generator.generate_all_files()
            
            if result['success']:
                return JsonResponse({
                    'message': 'FDA files generated successfully',
                    'files_generated': result['files_generated']
                })
            else:
                return JsonResponse({
                    'error': result.get('error', 'Unknown error'),
                    'errors': result.get('errors', [])
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error generating FDA files: {e}")
            return JsonResponse({'error': str(e)}, status=500)

class ResultsView(View):
    """Display results and download options"""
    
    def get(self, request, study_id):
        study = get_object_or_404(Study, study_id=study_id)
        extracted_domains = ExtractedDomain.objects.filter(study=study).select_related('domain')
        fda_files = FDAFile.objects.filter(study=study)
        
        # Calculate summary statistics
        total_records = sum(len(ed.content) if ed.content else 0 for ed in extracted_domains)
        
        context = {
            'study': study,
            'extracted_domains': extracted_domains,
            'fda_files': fda_files,
            'total_records': total_records,
            'total_domains': len(extracted_domains),
            'total_fda_files': len(fda_files)
        }
        
        return render(request, 'extraction/results.html', context)

class DownloadFileView(View):
    """Download extracted files"""
    
    def get(self, request, study_id, file_type, domain_code=None):
        try:
            study = get_object_or_404(Study, study_id=study_id)
            
            if file_type == 'xpt' and domain_code:
                # Download XPT file for specific domain
                extracted_domain = get_object_or_404(
                    ExtractedDomain,
                    study=study,
                    domain__code=domain_code
                )
                
                if not extracted_domain.xpt_file:
                    return HttpResponse('XPT file not found', status=404)
                
                response = HttpResponse(
                    extracted_domain.xpt_file.read(),
                    content_type='application/octet-stream'
                )
                response['Content-Disposition'] = f'attachment; filename="{domain_code}.xpt"'
                return response
                
            elif file_type == 'fda':
                # Download FDA file
                filename = request.GET.get('filename')
                if not filename:
                    return HttpResponse('Filename parameter required', status=400)
                
                fda_file = get_object_or_404(
                    FDAFile,
                    study=study,
                    name=filename
                )
                
                if not fda_file.file:
                    return HttpResponse('File not found', status=404)
                
                response = HttpResponse(
                    fda_file.file.read(),
                    content_type='application/octet-stream'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
                
            elif file_type == 'csv' and domain_code:
                # Download CSV version of domain data
                extracted_domain = get_object_or_404(
                    ExtractedDomain,
                    study=study,
                    domain__code=domain_code
                )
                
                if not extracted_domain.content:
                    return HttpResponse('No data found', status=404)
                
                import pandas as pd
                df = pd.DataFrame(extracted_domain.content)
                csv_content = df.to_csv(index=False)
                
                response = HttpResponse(csv_content, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{domain_code}.csv"'
                return response
            
            else:
                return HttpResponse('Invalid file type', status=400)
                
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return HttpResponse('Download failed', status=500)

class ExtractAllDomainsView(View):
    """Extract all detected domains at once"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, study_id):
        try:
            study = get_object_or_404(Study, study_id=study_id)
            detected_domains = DetectedDomain.objects.filter(study=study)
            
            if not detected_domains.exists():
                return JsonResponse({
                    'error': 'No detected domains found'
                }, status=400)
            
            # Start extraction for all domains
            extraction_threads = []
            
            for detected_domain in detected_domains:
                thread = threading.Thread(
                    target=self._run_single_extraction,
                    args=(study_id, detected_domain.domain.code)
                )
                thread.daemon = True
                thread.start()
                extraction_threads.append(thread)
            
            return JsonResponse({
                'message': f'Started extraction for {len(detected_domains)} domains',
                'domains': [dd.domain.code for dd in detected_domains]
            })
            
        except Exception as e:
            logger.error(f"Error starting bulk extraction: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _run_single_extraction(self, study_id: int, domain_code: str):
        """Run single domain extraction"""
        try:
            config = ExtractionConfig(validate_results=True)
            pipeline = ExtractionPipeline(config)
            result = pipeline.extract_domain(study_id, domain_code)
            
            logger.info(f"Bulk extraction {domain_code}: {'Success' if result['success'] else 'Failed'}")
            
        except Exception as e:
            logger.error(f"Bulk extraction failed for {domain_code}: {e}")


class DownloadAllFilesView(View):
    """Download all files (domain CSV, XPT, and FDA files) as a single ZIP"""
    
    def get(self, request, study_id):
        try:
            study = get_object_or_404(Study, study_id=study_id)
            extracted_domains = ExtractedDomain.objects.filter(study=study).select_related('domain')
            fda_files = FDAFile.objects.filter(study=study)
            
            # Check if there are any files to download
            if not extracted_domains.exists() and not fda_files.exists():
                return HttpResponse('No files available for download', status=404)
            
            # Create a BytesIO buffer to hold the zip file
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add domain CSV files
                for domain in extracted_domains:
                    if domain.content:
                        try:
                            # Create CSV from domain content
                            df = pd.DataFrame(domain.content)
                            csv_content = df.to_csv(index=False)
                            zip_file.writestr(f"domains/{domain.domain.code}.csv", csv_content)
                            logger.info(f"Added CSV for domain {domain.domain.code}")
                        except Exception as e:
                            logger.error(f"Error creating CSV for domain {domain.domain.code}: {e}")
                    
                    # Add XPT files if they exist
                    if domain.xpt_file:
                        try:
                            domain.xpt_file.seek(0)  # Reset file pointer
                            zip_file.writestr(f"domains/{domain.domain.code}.xpt", domain.xpt_file.read())
                            logger.info(f"Added XPT for domain {domain.domain.code}")
                        except Exception as e:
                            logger.error(f"Error adding XPT for domain {domain.domain.code}: {e}")
                
                # Add FDA files
                for fda_file in fda_files:
                    if fda_file.file:
                        try:
                            fda_file.file.seek(0)  # Reset file pointer
                            zip_file.writestr(f"fda/{fda_file.name}", fda_file.file.read())
                            logger.info(f"Added FDA file {fda_file.name}")
                        except Exception as e:
                            logger.error(f"Error adding FDA file {fda_file.name}: {e}")
                
                # Add a summary file
                summary_content = self._create_summary_file(study, extracted_domains, fda_files)
                zip_file.writestr("README.txt", summary_content)
            
            zip_buffer.seek(0)
            
            # Create response
            response = HttpResponse(zip_buffer.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="study_{study.study_number}_all_files.zip"'
            
            logger.info(f"Successfully created ZIP file for study {study.study_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error creating ZIP file for study {study_id}: {e}")
            return HttpResponse(f'Error creating ZIP file: {str(e)}', status=500)
    
    def _create_summary_file(self, study, extracted_domains, fda_files):
        """Create a summary file for the ZIP contents"""
        summary = f"""Study Data Export Summary
            ========================

            Study Information:
            - Study ID: {study.study_number}
            - Title: {study.title or 'N/A'}
            - Description: {study.description or 'N/A'}
            - Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            Extracted Domains ({len(extracted_domains)} total):
            """
        
        for domain in extracted_domains:
            record_count = len(domain.content) if domain.content else 0
            has_xpt = "Yes" if domain.xpt_file else "No"
            summary += f"- {domain.domain.code}: {record_count} records, XPT file: {has_xpt}\n"
        
        summary += f"\nFDA Files ({len(fda_files)} total):\n"
        for fda_file in fda_files:
            summary += f"- {fda_file.name}\n"
        
        summary += """
            File Structure:
            - domains/: Contains CSV and XPT files for each extracted domain
            - fda/: Contains FDA submission files
            - README.txt: This summary file

            Notes:
            - CSV files contain the extracted tabular data
            - XPT files are in SAS transport format for FDA submission
            - All files are organized by type for easy identification
            """
        
        return summary

