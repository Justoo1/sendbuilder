"""
PDFProcessor Utility for Toxicology Study Documents

This utility extracts text from complex PDF documents containing tables, 
comma-separated data, and mixed content formats, then saves the content 
page by page to the database.

Requirements:
pip install PyPDF2 pdfplumber pandas tabula-py
"""

import logging
import re
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError
import PyPDF2
import pdfplumber
import pandas as pd

from builder.models import Study, StudyContent

# Configure logging
logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Utility class for processing complex PDF documents and extracting text content.
    
    Handles:
    - Tables with various formats (comma-separated, space-separated, etc.)
    - Mixed content (text + tables)
    - Page-by-page extraction
    - Database storage
    """
    
    def __init__(self, study_obj, study_content_model):
        """
        Initialize the PDF processor.
        
        Args:
            study_obj: Study object containing the PDF file
            study_content_model: StudyContent model class for saving extracted content
        """
        self.study = study_obj
        self.StudyContent = study_content_model
        self.pdf_file = study_obj.study_file
        
    def process_pdf(self) -> Dict[str, Any]:
        """
        Main method to process the PDF and save content to database.
        
        Returns:
            Dict containing processing results and statistics
        """
        try:
            # Validate inputs
            self._validate_inputs()
            
            # Clear existing content for this study
            self._clear_existing_content()
            
            # Extract content from PDF
            extracted_pages = self._extract_pdf_content()
            
            # Save to database
            saved_count = self._save_to_database(extracted_pages)
            
            result = {
                'success': True,
                'total_pages': len(extracted_pages),
                'saved_pages': saved_count,
                'study_id': self.study.study_id,
                'message': f'Successfully processed {saved_count} pages'
            }
            
            logger.info(f"PDF processing completed: {result}")
            return result
            
        except Exception as e:
            error_msg = f"Error processing PDF for study {self.study.study_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'study_id': self.study.study_id
            }
    
    def _validate_inputs(self):
        """Validate that required inputs are present and valid."""
        if not self.study:
            raise ValidationError("Study object is required")
        
        if not hasattr(self.study, 'study_file') or not self.study.study_file:
            raise ValidationError("Study must have a study_file field with a PDF")
        
        # Check if file exists and is accessible
        try:
            self.pdf_file.open()
            self.pdf_file.close()
        except Exception as e:
            raise ValidationError(f"Cannot access PDF file: {str(e)}")
    
    def _clear_existing_content(self):
        """Clear any existing content for this study."""
        deleted_count = self.StudyContent.objects.filter(study=self.study).count()
        if deleted_count > 0:
            self.StudyContent.objects.filter(study=self.study).delete()
            logger.info(f"Cleared {deleted_count} existing content records for study {self.study.study_id}")
    
    def _extract_pdf_content(self) -> List[Dict[str, Any]]:
        """
        Extract content from PDF using multiple methods for complex documents.
        
        Returns:
            List of dictionaries containing page content and metadata
        """
        extracted_pages = []
        
        # Method 1: Try pdfplumber (best for tables and complex layouts)
        try:
            extracted_pages = self._extract_with_pdfplumber()
            if extracted_pages:
                logger.info("Successfully extracted content using pdfplumber")
                return extracted_pages
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {str(e)}")
        
        # Method 2: Fallback to PyPDF2 (basic text extraction)
        try:
            extracted_pages = self._extract_with_pypdf2()
            logger.info("Successfully extracted content using PyPDF2")
            return extracted_pages
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {str(e)}")
            raise Exception("All PDF extraction methods failed")
    
    def _extract_with_pdfplumber(self) -> List[Dict[str, Any]]:
        """Extract content using pdfplumber (handles tables well)."""
        extracted_pages = []
        
        with pdfplumber.open(self.pdf_file.path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # Extract text content
                    text_content = page.extract_text() or ""
                    
                    # Extract tables
                    tables = page.extract_tables()
                    table_content = self._process_tables(tables)
                    
                    # Combine text and table content
                    combined_content = self._combine_content(text_content, table_content)
                    
                    # Clean and normalize content
                    cleaned_content = self._clean_content(combined_content)
                    
                    if cleaned_content.strip():  # Only save if content exists
                        extracted_pages.append({
                            'page_number': page_num,
                            'content': cleaned_content,
                            'has_tables': len(tables) > 0,
                            'table_count': len(tables)
                        })
                    
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num}: {str(e)}")
                    # Continue with next page
                    continue
        
        return extracted_pages
    
    def _extract_with_pypdf2(self) -> List[Dict[str, Any]]:
        """Fallback extraction using PyPDF2."""
        extracted_pages = []
        
        with open(self.pdf_file.path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
                    cleaned_content = self._clean_content(text)
                    
                    if cleaned_content.strip():
                        extracted_pages.append({
                            'page_number': page_num,
                            'content': cleaned_content,
                            'has_tables': False,
                            'table_count': 0
                        })
                
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num} with PyPDF2: {str(e)}")
                    continue
        
        return extracted_pages
    
    def _process_tables(self, tables: List[List[List[str]]]) -> str:
        """
        Process extracted tables and convert to readable text format.
        
        Args:
            tables: List of tables from pdfplumber
            
        Returns:
            Formatted string representation of tables
        """
        if not tables:
            return ""
        
        table_content = []
        
        for i, table in enumerate(tables):
            if not table:
                continue
                
            table_content.append(f"\n--- TABLE {i + 1} ---")
            
            # Convert table to DataFrame for better handling
            try:
                df = pd.DataFrame(table)
                
                # Remove completely empty rows and columns
                df = df.dropna(how='all').dropna(axis=1, how='all')
                
                if not df.empty:
                    # Convert to string with proper formatting
                    table_str = df.to_string(index=False, na_rep='')
                    table_content.append(table_str)
                    
            except Exception as e:
                # Fallback: simple text representation
                logger.warning(f"Error processing table {i + 1}: {str(e)}")
                for row in table:
                    if row:
                        # Join non-empty cells with tabs
                        row_text = '\t'.join([cell or '' for cell in row if cell])
                        if row_text.strip():
                            table_content.append(row_text)
        
        return '\n'.join(table_content)
    
    def _combine_content(self, text_content: str, table_content: str) -> str:
        """Combine text and table content intelligently."""
        content_parts = []
        
        if text_content and text_content.strip():
            content_parts.append("--- TEXT CONTENT ---")
            content_parts.append(text_content)
        
        if table_content and table_content.strip():
            content_parts.append("--- TABLE CONTENT ---")
            content_parts.append(table_content)
        
        return '\n\n'.join(content_parts)
    
    def _clean_content(self, content: str) -> str:
        """
        Clean and normalize extracted content.
        
        Args:
            content: Raw extracted content
            
        Returns:
            Cleaned content string
        """
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Remove trailing/leading whitespace from each line
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(lines)
        
        # Remove excessive spaces within lines
        content = re.sub(r' +', ' ', content)
        
        # Handle common PDF extraction artifacts
        content = content.replace('\x00', '')  # Remove null characters
        content = content.replace('\ufffd', '')  # Remove replacement characters
        
        return content.strip()
    
    @transaction.atomic
    def _save_to_database(self, extracted_pages: List[Dict[str, Any]]) -> int:
        """
        Save extracted content to database using atomic transaction.
        
        Args:
            extracted_pages: List of page data dictionaries
            
        Returns:
            Number of pages saved
        """
        saved_count = 0
        
        for page_data in extracted_pages:
            try:
                content_obj = self.StudyContent.objects.create(
                    study=self.study,
                    content=page_data['content'],
                    page=page_data['page_number']
                )
                saved_count += 1
                logger.debug(f"Saved content for page {page_data['page_number']}")
                
            except Exception as e:
                logger.error(f"Error saving page {page_data['page_number']}: {str(e)}")
                # Continue with other pages in atomic transaction
                continue
        
        return saved_count


# Utility function for easy usage
def process_study_pdf(study_obj, study_content_model=None):
    """
    Convenience function to process a study PDF.
    
    Args:
        study_obj: Study instance with study_file field
        study_content_model: StudyContent model class (optional)
        
    Returns:
        Processing result dictionary
    """
    # Import here to avoid circular imports
    if study_content_model is None:
        study_content_model = StudyContent
    
    processor = PDFProcessor(study_obj, study_content_model)
    return processor.process_pdf()


# Example usage functions
def process_single_study(study_id: int):
    """Process a single study by ID."""
    
    try:
        study = Study.objects.get(study_id=study_id)
        result = process_study_pdf(study, StudyContent)
        return result
    except Study.DoesNotExist:
        return {'success': False, 'error': f'Study with ID {study_id} not found'}


def process_all_unprocessed_studies():
    """Process all studies that don't have content yet."""
    
    # Find studies without content
    studies_without_content = Study.objects.filter(
        studycontent__isnull=True
    ).distinct()
    
    results = []
    for study in studies_without_content:
        if study.study_file:
            result = process_study_pdf(study, StudyContent)
            results.append(result)
    
    return results


def reprocess_study(study_id: int):
    """Reprocess a study (clears existing content first)."""
    return process_single_study(study_id)  # The processor handles clearing existing content


# Example integration with Django views
# def study_upload_view(request, study_id):
#     """Example view that processes PDF after upload."""
#     from your_app.models import Study, StudyContent
    
#     study = Study.objects.get(id=study_id)
    
#     if request.method == 'POST' and study.study_file:
#         # Process PDF in background or immediately
#         result = process_study_pdf(study, StudyContent)
        
#         if result['success']:
#             messages.success(request, f"PDF processed successfully: {result['message']}")
#         else:
#             messages.error(request, f"PDF processing failed: {result['error']}")
    
#     return redirect('study_detail', study_id=study_id)