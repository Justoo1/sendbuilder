# extraction/pipeline.py
import logging
import io
from io import StringIO
import pandas as pd
from typing import Dict, List, Any, Optional, TypedDict
from dataclasses import dataclass
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from django.core.files.base import ContentFile
from django.db import transaction

from builder.models import Study, DetectedDomain, StudyContent, ExtractedDomain, FDAFile
from ..ai_model.config import ai_config
from .prompts import ExtractionPrompts
from builder.utils.send_utils import get_required_columns
from .send_validator import post_process_domain_data

logger = logging.getLogger(__name__)

@dataclass
class ExtractionConfig:
    """Configuration for extraction pipeline"""
    chunk_size: int = 6000
    max_retries: int = 3
    validate_results: bool = True
    save_intermediate: bool = False

class SimpleExtractionPipeline:
    """Simplified extraction pipeline using only LangChain"""
    
    def __init__(self, config: ExtractionConfig = None):
        self.config = config or ExtractionConfig()
        self.llm = None
        self.prompts = ExtractionPrompts()
        self.output_parser = StrOutputParser()
    
    def _initialize_llm(self) -> bool:
        """Initialize the LLM from AIModel configuration"""
        try:
            self.llm = ai_config.create_langchain_model('CHAT')
            if not self.llm:
                logger.error("Failed to create LLM from AIModel configuration")
                return False
            logger.info(f"Initialized LLM: {ai_config.get_model_config('CHAT')}")
            return True
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            return False
    
    def extract_domain(self, study_id: int, domain_code: str) -> Dict[str, Any]:
        """Main entry point for domain extraction"""
        logger.info(f"Starting extraction for study {study_id}, domain {domain_code}")
        logger.debug(f"Extraction config: chunk_size={self.config.chunk_size}, max_retries={self.config.max_retries}")
    
        # Initialize LLM
        logger.debug("Initializing LLM...")
        if not self._initialize_llm():
            logger.error("Failed to initialize LLM - returning error")
            return {"success": False, "error": "Failed to initialize LLM"}
        
        logger.debug("LLM initialized successfully")

        # Get detected domain info
        logger.debug(f"Looking up DetectedDomain for study_id={study_id}, domain__code={domain_code}")
        
        # Get detected domain info
        try:
            detected_domain = DetectedDomain.objects.get(
                study_id=study_id, 
                domain__code=domain_code
            )
            pages = detected_domain.page
            logger.debug(f"Found detected domain: {domain_code} with {len(pages)} pages: {pages}")
            logger.debug(f"Detected domain confidence: {detected_domain.confident_score}")
        except DetectedDomain.DoesNotExist:
            logger.debug(f"No detected domain found for study {study_id}, domain {domain_code}")
            return {"success": False, "error": f"Domain {domain_code} not detected for study {study_id}"}
        
        logger.debug("Creating extraction state...")
        
        # Initialize extraction state
        extraction_state = {
            'study_id': study_id,
            'domain_code': domain_code,
            'pages': pages,
            'extracted_chunks': [],
            'errors': [],
            'start_time': datetime.now()
        }
        
        try:
            # Step 1: Extract from each page
            for page_idx, page_num in enumerate(pages):
                logger.info(f"Processing page {page_num} ({page_idx + 1}/{len(pages)})")
                
                chunk_result = self._extract_from_page(
                    study_id, domain_code, page_num, page_idx + 1, len(pages)
                )
                
                if chunk_result['success']:
                    extraction_state['extracted_chunks'].append(chunk_result['data'])
                    logger.info(f"Successfully extracted data from page {page_num}")
                else:
                    error_msg = f"Failed to extract from page {page_num}: {chunk_result['error']}"
                    extraction_state['errors'].append(error_msg)
                    logger.warning(error_msg)
                    # Continue with other pages instead of failing completely
            
            # Check if we have any extracted data
            if not extraction_state['extracted_chunks']:
                return {
                    "success": False, 
                    "error": "No data extracted from any page",
                    "errors": extraction_state['errors']
                }
            
            # Step 2: Combine chunks if multiple
            combined_data = self._combine_chunks(extraction_state['extracted_chunks'], domain_code)
            if not combined_data:
                return {
                    "success": False, 
                    "error": "Failed to combine extracted chunks",
                    "errors": extraction_state['errors']
                }
            
            # Step 3: Parse and validate data
            df = self._parse_and_validate(combined_data, domain_code)
            if df is None or df.empty:
                return {
                    "success": False, 
                    "error": "Failed to parse combined data into valid DataFrame",
                    "errors": extraction_state['errors']
                }
            
            # Step 4: Post-process data
            processed_df = post_process_domain_data(df, domain_code)
            
            # Step 5: Save results
            save_result = self._save_results(study_id, domain_code, processed_df)
            if not save_result['success']:
                return {
                    "success": False,
                    "error": save_result['error'],
                    "errors": extraction_state['errors']
                }
            
            # Return success
            return {
                "success": True,
                "data": processed_df.to_dict('records'),
                "metadata": {
                    "record_count": len(processed_df),
                    "pages_processed": len(pages),
                    "processing_time": (datetime.now() - extraction_state['start_time']).total_seconds(),
                    "model_config": ai_config.get_model_config('CHAT')
                },
                "errors": extraction_state['errors']  # Include any non-fatal errors
            }
            
        except Exception as e:
            logger.error(f"Extraction failed for {domain_code}: {e}", exc_info=True)
            return {
                "success": False, 
                "error": str(e),
                "errors": extraction_state['errors']
            }
    
    def _extract_from_page(self, study_id: int, domain_code: str, page_num: int, 
                          current_page: int, total_pages: int) -> Dict[str, Any]:
        """Extract data from a single page with retries"""
        
        # Get page content
        try:
            content_obj = StudyContent.objects.get(study_id=study_id, page=page_num)
            content = content_obj.content
        except StudyContent.DoesNotExist:
            return {"success": False, "error": f"Content not found for page {page_num}"}
        
        if not content.strip():
            return {"success": False, "error": f"Empty content for page {page_num}"}
        
        # Try extraction with retries
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"Extraction attempt {attempt + 1}/{self.config.max_retries} for page {page_num}")
                
                # Create extraction prompt
                chunk_info = {"current": current_page, "total": total_pages}
                prompt_text = self.prompts.get_domain_extraction_prompt(
                    domain_code, content, chunk_info
                )
                
                # Create prompt template and chain
                prompt_template = PromptTemplate(
                    template="{system_prompt}\n\n{extraction_prompt}",
                    input_variables=["system_prompt", "extraction_prompt"]
                )
                
                extraction_chain = prompt_template | self.llm | self.output_parser
                
                # Extract data
                response = extraction_chain.invoke({
                    "system_prompt": self.prompts.get_system_prompt(),
                    "extraction_prompt": prompt_text
                })
                
                # Clean and validate response
                cleaned_csv = self._clean_csv_response(response)
                if not cleaned_csv:
                    logger.warning(f"No valid CSV data in response for page {page_num}, attempt {attempt + 1}")
                    continue
                
                # Quick validation - try to parse as CSV
                try:
                    test_df = pd.read_csv(StringIO(cleaned_csv))
                    if test_df.empty:
                        logger.warning(f"Empty DataFrame from page {page_num}, attempt {attempt + 1}")
                        continue
                    
                    # Check for required columns
                    required_cols = get_required_columns(domain_code)
                    missing_cols = [col for col in required_cols[:3] if col not in test_df.columns]  # Check first 3 critical columns
                    
                    if len(missing_cols) == len(required_cols[:3]):  # All critical columns missing
                        logger.warning(f"Critical columns missing from page {page_num}, attempt {attempt + 1}")
                        continue
                    
                    logger.info(f"Successfully extracted valid data from page {page_num}")
                    return {"success": True, "data": cleaned_csv}
                    
                except Exception as parse_error:
                    logger.warning(f"CSV parsing failed for page {page_num}, attempt {attempt + 1}: {parse_error}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Extraction attempt {attempt + 1} failed for page {page_num}: {e}")
                continue
        
        # All attempts failed
        return {"success": False, "error": f"All {self.config.max_retries} extraction attempts failed for page {page_num}"}
    
    def _combine_chunks(self, chunks: List[str], domain_code: str) -> Optional[str]:
        """Combine multiple CSV chunks into one"""
        if not chunks:
            return None
        
        if len(chunks) == 1:
            return chunks[0]
        
        try:
            # Use LLM to intelligently combine chunks
            combine_prompt = self.prompts.get_chunk_combination_prompt(domain_code, chunks)
            
            prompt_template = PromptTemplate(
                template="{combine_prompt}",
                input_variables=["combine_prompt"]
            )
            
            combination_chain = prompt_template | self.llm | self.output_parser
            combined_response = combination_chain.invoke({"combine_prompt": combine_prompt})
            
            # Clean the response
            cleaned_combined = self._clean_csv_response(combined_response)
            
            if cleaned_combined:
                logger.info(f"Successfully combined {len(chunks)} chunks using LLM")
                return cleaned_combined
            else:
                # Fallback: simple concatenation
                logger.warning("LLM combination failed, using fallback method")
                return self._simple_combine_chunks(chunks)
                
        except Exception as e:
            logger.warning(f"LLM chunk combination failed: {e}, using fallback")
            return self._simple_combine_chunks(chunks)
    
    def _simple_combine_chunks(self, chunks: List[str]) -> Optional[str]:
        """Simple fallback method to combine chunks"""
        try:
            all_dfs = []
            headers = None
            
            for chunk in chunks:
                df = pd.read_csv(StringIO(chunk))
                if not df.empty:
                    if headers is None:
                        headers = df.columns.tolist()
                    # Ensure consistent columns
                    for col in headers:
                        if col not in df.columns:
                            df[col] = ""
                    all_dfs.append(df[headers])  # Ensure column order
            
            if all_dfs:
                combined_df = pd.concat(all_dfs, ignore_index=True)
                return combined_df.to_csv(index=False)
            
        except Exception as e:
            logger.error(f"Simple chunk combination failed: {e}")
        
        return None
    
    def _parse_and_validate(self, csv_data: str, domain_code: str) -> Optional[pd.DataFrame]:
        """Parse CSV data and perform basic validation"""
        try:
            df = pd.read_csv(StringIO(csv_data))
            
            if df.empty:
                logger.error("Parsed DataFrame is empty")
                return None
            
            # Ensure required columns exist
            required_cols = get_required_columns(domain_code)
            for col in required_cols:
                if col not in df.columns:
                    if col == 'DOMAIN':
                        df[col] = domain_code
                    elif col.endswith('SEQ'):
                        df[col] = range(1, len(df) + 1)
                    else:
                        df[col] = ""
            
            logger.info(f"Parsed and validated DataFrame with {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error parsing/validating CSV data: {e}")
            return None
    
    def _save_results(self, study_id: int, domain_code: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Save extracted data to database"""
        try:
            with transaction.atomic():
                # Get or create ExtractedDomain
                extracted_domain, created = ExtractedDomain.objects.get_or_create(
                    study_id=study_id,
                    domain__code=domain_code,
                    defaults={'content': df.to_dict('records')}
                )
                
                if not created:
                    extracted_domain.content = df.to_dict('records')
                    extracted_domain.save()
                
                # Generate XPT file
                xpt_content = self._generate_xpt_file(df, domain_code)
                if xpt_content:
                    xpt_file = ContentFile(xpt_content, name=f"{domain_code}.xpt")
                    extracted_domain.xpt_file.save(f"{domain_code}.xpt", xpt_file, save=True)
                
                logger.info(f"Saved {len(df)} records for domain {domain_code}")
                return {"success": True, "extracted_domain_id": extracted_domain.id}
                
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return {"success": False, "error": str(e)}
    
    def _clean_csv_response(self, response: str) -> str:
        """Clean the LLM response to extract valid CSV data"""
        import re
        
        if not response or not response.strip():
            return ""
        
        # Remove code block markers
        response = re.sub(r'```(?:csv)?\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        # Extract lines that look like CSV
        lines = response.split('\n')
        csv_lines = []
        found_header = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for header line (starts with STUDYID typically)
            if not found_header and ('STUDYID' in line.upper() or 'DOMAIN' in line.upper()):
                found_header = True
                csv_lines.append(line)
            elif found_header and ',' in line and not line.startswith('#'):
                csv_lines.append(line)
        
        result = '\n'.join(csv_lines) if csv_lines else ""
        
        # Final validation - must have at least header + 1 data row
        if result and len(result.split('\n')) >= 2:
            return result
        
        return ""
    
    def _generate_xpt_file(self, df: pd.DataFrame, domain_code: str) -> Optional[bytes]:
        """Generate XPT file from DataFrame"""
        try:
            # For now, return CSV as bytes (placeholder for actual XPT generation)
            return df.to_csv(index=False).encode('utf-8')
        except Exception as e:
            logger.error(f"Error generating XPT file: {e}")
            return None


# For backward compatibility, create an alias
ExtractionPipeline = SimpleExtractionPipeline