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
from builder.models import Study

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
        
        # ADDED: Get the Study object for context
        try:
            study = Study.objects.get(pk=study_id)
            logger.info(f"Found study: {study.study_number} - {study.title}")
        except Study.DoesNotExist:
            logger.error(f"Study with ID {study_id} not found")
            return {"success": False, "error": f"Study with ID {study_id} not found"}
        
        # Initialize LLM
        logger.debug("Initializing LLM...")
        if not self._initialize_llm():
            logger.error("Failed to initialize LLM - returning error")
            return {"success": False, "error": "Failed to initialize LLM"}
        
        logger.debug("LLM initialized successfully")
        
        # Get detected domain info
        logger.debug(f"Looking up DetectedDomain for study_id={study_id}, domain__code={domain_code}")
        
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
            'start_time': datetime.now(),
            'study': study  # ADDED: Include study object in state
        }
        
        try:
            # Step 1: Extract from each page
            for page_idx, page_num in enumerate(pages):
                logger.info(f"Processing page {page_num} ({page_idx + 1}/{len(pages)})")
                
                # MODIFIED: Pass study context to extraction
                chunk_result = self._extract_from_page(
                    study_id, domain_code, page_num, page_idx + 1, len(pages), study
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
            
            logger.info(f"Completed page extraction. Starting chunk combination for {len(extraction_state['extracted_chunks'])} chunks")
            
            # Step 2: Combine chunks if multiple - IMPROVED METHOD
            combined_data = self._combine_chunks_efficiently(extraction_state['extracted_chunks'], domain_code)
            if not combined_data:
                return {
                    "success": False, 
                    "error": "Failed to combine extracted chunks",
                    "errors": extraction_state['errors']
                }
            
            logger.info("Successfully combined chunks")
            
            # Step 3: Parse and validate data
            logger.info("Parsing and validating combined data")
            df = self._parse_and_validate(combined_data, domain_code)
            if df is None or df.empty:
                return {
                    "success": False, 
                    "error": "Failed to parse combined data into valid DataFrame",
                    "errors": extraction_state['errors']
                }
            
            logger.info(f"Successfully parsed data into DataFrame with {len(df)} records")
            
            # Step 4: Post-process data - MODIFIED to pass study object
            logger.info("Post-processing data with study context")
            logger.debug(f"Pre-processing DataFrame: {len(df)} records, columns: {list(df.columns)}")
            logger.debug(f"Sample data:\n{df.head(3).to_string()}")
            
            # FIXED: Pass study object to post_process_domain_data
            processed_df = post_process_domain_data(df, domain_code, study)
            logger.info(f"Post-processing complete. Final record count: {len(processed_df)}")
            logger.debug(f"Post-processed DataFrame columns: {list(processed_df.columns)}")
            
            if len(processed_df) != len(df):
                logger.warning(f"Post-processing changed record count from {len(df)} to {len(processed_df)}")
                logger.debug(f"Post-processed sample data:\n{processed_df.head(3).to_string()}")
            
            # Step 5: Save results
            logger.info("Saving results to database")
            save_result = self._save_results(study_id, domain_code, processed_df)
            if not save_result['success']:
                return {
                    "success": False,
                    "error": save_result['error'],
                    "errors": extraction_state['errors']
                }
            
            logger.info(f"Successfully saved {len(processed_df)} records to database")
            
            # Return success
            return {
                "success": True,
                "data": processed_df.to_dict('records'),
                "metadata": {
                    "record_count": len(processed_df),
                    "pages_processed": len(pages),
                    "processing_time": (datetime.now() - extraction_state['start_time']).total_seconds(),
                    "model_config": ai_config.get_model_config('CHAT'),
                    "study_number": study.study_number  # ADDED: Include study context in response
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
                      current_page: int, total_pages: int, study=None) -> Dict[str, Any]:
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
                
                # Create extraction prompt with study context
                chunk_info = {"current": current_page, "total": total_pages}
                
                # MODIFIED: Pass study context to prompt generation
                prompt_text = self.prompts.get_domain_extraction_prompt(
                    domain_code, content, chunk_info, study
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
                
                # Quick validation - try to parse as CSV with error handling
                try:
                    # Try with different CSV parsing options for problematic data
                    test_df = pd.read_csv(
                        StringIO(cleaned_csv),
                        on_bad_lines='skip',  # Skip problematic lines
                        quoting=1,  # QUOTE_ALL
                        skipinitialspace=True
                    )
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
                    
                    # Try to fix the CSV by cleaning up problematic characters
                    try:
                        fixed_csv = self._fix_csv_formatting(cleaned_csv)
                        test_df = pd.read_csv(StringIO(fixed_csv))
                        if not test_df.empty:
                            logger.info(f"Successfully fixed and extracted data from page {page_num}")
                            return {"success": True, "data": fixed_csv}
                    except Exception as fix_error:
                        logger.warning(f"CSV fix attempt failed for page {page_num}: {fix_error}")
                    
                    continue
                    
            except Exception as e:
                logger.warning(f"Extraction attempt {attempt + 1} failed for page {page_num}: {e}")
                continue
        
        # All attempts failed
        return {"success": False, "error": f"All {self.config.max_retries} extraction attempts failed for page {page_num}"}
    
    def _combine_chunks_efficiently(self, chunks: List[str], domain_code: str) -> Optional[str]:
        """Efficiently combine multiple CSV chunks using pandas instead of LLM"""
        if not chunks:
            logger.error("No chunks to combine")
            return None
        
        if len(chunks) == 1:
            logger.info("Only one chunk, returning directly")
            return chunks[0]
        
        logger.info(f"Combining {len(chunks)} chunks using pandas method")
        
        try:
            all_dfs = []
            
            # Parse each chunk into DataFrame
            for i, chunk in enumerate(chunks):
                try:
                    logger.debug(f"Parsing chunk {i + 1}/{len(chunks)}")
                    
                    # Try parsing with different options for robustness
                    try:
                        df = pd.read_csv(StringIO(chunk))
                    except Exception as e:
                        logger.debug(f"Standard CSV parsing failed for chunk {i + 1}, trying with error handling: {e}")
                        df = pd.read_csv(
                            StringIO(chunk),
                            on_bad_lines='skip',
                            quoting=1,
                            skipinitialspace=True
                        )
                    
                    if not df.empty:
                        logger.debug(f"Chunk {i + 1} has {len(df)} records with columns: {list(df.columns)}")
                        all_dfs.append(df)
                    else:
                        logger.warning(f"Chunk {i + 1} is empty, skipping")
                        
                except Exception as e:
                    logger.warning(f"Failed to parse chunk {i + 1}: {e}")
                    continue
            
            if not all_dfs:
                logger.error("No valid DataFrames after parsing chunks")
                return None
            
            logger.info(f"Successfully parsed {len(all_dfs)} DataFrames")
            
            # Ensure all DataFrames have consistent columns
            logger.debug("Standardizing columns across DataFrames")
            all_columns = set()
            for df in all_dfs:
                all_columns.update(df.columns)
            
            all_columns = sorted(list(all_columns))
            logger.debug(f"All unique columns: {all_columns}")
            
            # Ensure each DataFrame has all columns
            standardized_dfs = []
            for i, df in enumerate(all_dfs):
                for col in all_columns:
                    if col not in df.columns:
                        df[col] = ""
                
                # Reorder columns consistently
                df = df[all_columns]
                standardized_dfs.append(df)
                logger.debug(f"Standardized DataFrame {i + 1}: {len(df)} records")
            
            # Combine all DataFrames
            logger.info("Concatenating all DataFrames")
            combined_df = pd.concat(standardized_dfs, ignore_index=True)
            
            # Remove duplicate rows if any
            original_count = len(combined_df)
            combined_df = combined_df.drop_duplicates()
            final_count = len(combined_df)
            
            if original_count != final_count:
                logger.info(f"Removed {original_count - final_count} duplicate rows")
            
            logger.info(f"Successfully combined chunks into DataFrame with {final_count} records")
            
            # Convert back to CSV
            result_csv = combined_df.to_csv(index=False)
            return result_csv
            
        except Exception as e:
            logger.error(f"Efficient chunk combination failed: {e}", exc_info=True)
            
            # Fallback to simple concatenation
            logger.info("Attempting fallback simple combination")
            return self._simple_combine_chunks(chunks)
    
    def _simple_combine_chunks(self, chunks: List[str]) -> Optional[str]:
        """Simple fallback method to combine chunks"""
        try:
            logger.info(f"Using simple combination method for {len(chunks)} chunks")
            
            all_lines = []
            header_added = False
            
            for i, chunk in enumerate(chunks):
                lines = chunk.strip().split('\n')
                
                if not lines:
                    continue
                
                # Add header from first chunk only
                if not header_added and lines:
                    all_lines.append(lines[0])  # Header
                    header_added = True
                
                # Add data lines (skip header)
                for line in lines[1:]:
                    if line.strip():
                        all_lines.append(line)
            
            if all_lines:
                result = '\n'.join(all_lines)
                logger.info(f"Simple combination produced {len(all_lines)} total lines")
                return result
            else:
                logger.error("Simple combination produced no output")
                return None
                
        except Exception as e:
            logger.error(f"Simple chunk combination failed: {e}")
            return None
    
    def _parse_and_validate(self, csv_data: str, domain_code: str) -> Optional[pd.DataFrame]:
        """Parse CSV data and perform basic validation"""
        try:
            logger.debug("Parsing CSV data into DataFrame")
            
            # Try different parsing strategies
            try:
                df = pd.read_csv(StringIO(csv_data))
            except Exception as e:
                logger.debug(f"Standard CSV parsing failed, trying with error handling: {e}")
                df = pd.read_csv(
                    StringIO(csv_data),
                    on_bad_lines='skip',
                    quoting=1,
                    skipinitialspace=True
                )
            
            if df.empty:
                logger.error("Parsed DataFrame is empty")
                return None
            
            logger.debug(f"Parsed DataFrame: {len(df)} rows, {len(df.columns)} columns")
            logger.debug(f"Columns: {list(df.columns)}")
            
            # Ensure required columns exist
            required_cols = get_required_columns(domain_code)
            logger.debug(f"Required columns for {domain_code}: {required_cols}")
            
            for col in required_cols:
                if col not in df.columns:
                    if col == 'DOMAIN':
                        df[col] = domain_code
                        logger.debug(f"Added missing column {col} with value: {domain_code}")
                    elif col.endswith('SEQ'):
                        df[col] = range(1, len(df) + 1)
                        logger.debug(f"Added missing column {col} with sequence numbers")
                    else:
                        df[col] = ""
                        logger.debug(f"Added missing column {col} with empty values")
            
            logger.info(f"Parsed and validated DataFrame with {len(df)} records, {len(df.columns)} columns")
            return df
            
        except Exception as e:
            logger.error(f"Error parsing/validating CSV data: {e}", exc_info=True)
            return None
    
    def _save_results(self, study_id: int, domain_code: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Save extracted data to database"""
        try:
            logger.debug(f"Starting database save for {len(df)} records")
            
            with transaction.atomic():
                # Get the Domain object first
                logger.debug(f"Looking up Domain object for code: {domain_code}")
                df_for_json = df.fillna(value='-')
                try:
                    from builder.models import Domain
                    domain = Domain.objects.get(code=domain_code)
                    logger.debug(f"Found domain: {domain.id} - {domain.code}")
                except Domain.DoesNotExist:
                    logger.error(f"Domain with code '{domain_code}' not found")
                    return {"success": False, "error": f"Domain '{domain_code}' not found in database"}
                
                # Get or create ExtractedDomain
                logger.debug("Creating/updating ExtractedDomain record")
                extracted_domain, created = ExtractedDomain.objects.get_or_create(
                    study_id=study_id,
                    domain=domain,  # Use domain object instead of domain__code
                    defaults={'content': df_for_json.to_dict('records')}
                )
                
                if not created:
                    logger.debug("Updating existing ExtractedDomain record")
                    extracted_domain.content = df_for_json.to_dict('records')
                    extracted_domain.save()
                else:
                    logger.debug("Created new ExtractedDomain record")
                
                # Generate XPT file
                logger.debug("Generating XPT file")
                xpt_content = self._generate_xpt_file(df, domain_code)
                if xpt_content:
                    xpt_file = ContentFile(xpt_content, name=f"{domain_code}.xpt")
                    extracted_domain.xpt_file.save(f"{domain_code}.xpt", xpt_file, save=True)
                    logger.info(f"XPT file saved successfully: {len(xpt_content)} bytes")
                else:
                    logger.warning("XPT file generation failed")
                
                logger.info(f"Successfully saved {len(df)} records for domain {domain_code} (ExtractedDomain ID: {extracted_domain.id})")
                return {"success": True, "extracted_domain_id": extracted_domain.id}
                
        except Exception as e:
            logger.error(f"Error saving results: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        
    
    def _fix_csv_formatting(self, csv_data: str) -> str:
        """Fix common CSV formatting issues"""
        import re
        
        lines = csv_data.split('\n')
        fixed_lines = []
        
        for line in lines:
            if not line.strip():
                continue
                
            # Remove any trailing/leading quotes that might be causing issues
            line = line.strip()
            
            # Fix common issues with embedded commas and quotes
            # If line has uneven quotes, try to balance them
            quote_count = line.count('"')
            if quote_count % 2 != 0:
                # Odd number of quotes - try to fix by escaping internal quotes
                parts = line.split(',')
                fixed_parts = []
                for part in parts:
                    part = part.strip()
                    if '"' in part and not (part.startswith('"') and part.endswith('"')):
                        # Escape internal quotes
                        part = '"' + part.replace('"', '""') + '"'
                    fixed_parts.append(part)
                line = ','.join(fixed_parts)
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
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
        """Generate proper XPT file from DataFrame using pyreadstat"""
        logger.debug(f"Generating XPT file for domain {domain_code} with {len(df)} records")
        
        try:
            import pyreadstat
            import tempfile
            import os
            
            # Prepare DataFrame for SAS format
            df_sas = self._prepare_dataframe_for_sas(df, domain_code)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.xpt', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            try:
                # Create variable labels dictionary
                variable_labels = {}
                for col in df_sas.columns:
                    if col == 'STUDYID':
                        variable_labels[col] = 'Study Identifier'
                    elif col == 'DOMAIN':
                        variable_labels[col] = 'Domain Abbreviation'
                    elif col == 'USUBJID':
                        variable_labels[col] = 'Unique Subject Identifier'
                    elif col.endswith('SEQ'):
                        variable_labels[col] = 'Sequence Number'
                    else:
                        variable_labels[col] = col.replace('_', ' ').title()
                
                # Write XPT file using pyreadstat - CORRECTED PARAMETERS
                pyreadstat.write_xport(
                    df_sas,
                    temp_path,
                    table_name=domain_code.upper()[:8],
                    file_format_version=5
                )
                
                # Read the generated file
                with open(temp_path, 'rb') as f:
                    xpt_content = f.read()
                
                logger.info(f"Generated XPT file with pyreadstat: {len(xpt_content)} bytes")
                return xpt_content
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except ImportError:
            logger.warning("pyreadstat not available, falling back to CSV")
            return self._generate_csv_as_xpt_fallback(df, domain_code)
        except Exception as e:
            logger.error(f"Error generating XPT file: {e}", exc_info=True)
            logger.warning("Falling back to CSV format")
            return self._generate_csv_as_xpt_fallback(df, domain_code)
    def _generate_csv_as_xpt_fallback(self, df: pd.DataFrame, domain_code: str) -> Optional[bytes]:
        """Fallback method - save as CSV with .xpt extension for compatibility"""
        try:
            logger.debug("Using CSV fallback for XPT generation")
            csv_content = df.to_csv(index=False)
            return csv_content.encode('utf-8')
        except Exception as e:
            logger.error(f"Error generating CSV fallback: {e}")
            return None

    def _generate_xpt_with_pyreadstat(self, df: pd.DataFrame, domain_code: str) -> Optional[bytes]:
        """Generate XPT using pyreadstat - most SAS-compatible method"""
        import pyreadstat
        import tempfile
        import os
        
        try:
            # Prepare DataFrame for SAS format
            df_sas = self._prepare_dataframe_for_sas(df, domain_code)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.xpt', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            try:
                # Create variable labels dictionary
                variable_labels = {}
                for col in df_sas.columns:
                    if col == 'STUDYID':
                        variable_labels[col] = 'Study Identifier'
                    elif col == 'DOMAIN':
                        variable_labels[col] = 'Domain Abbreviation'
                    elif col == 'USUBJID':
                        variable_labels[col] = 'Unique Subject Identifier'
                    elif col.endswith('SEQ'):
                        variable_labels[col] = 'Sequence Number'
                    else:
                        variable_labels[col] = col.replace('_', ' ').title()
                
                # Write XPT file using pyreadstat
                pyreadstat.write_xport(
                    df_sas,
                    temp_path,
                    table_name=domain_code.upper()[:8],  # SAS table name limit
                    label=f"{domain_code} Domain Data",
                    variable_labels=variable_labels,
                    file_encoding='utf-8'
                )
                
                # Read the generated file
                with open(temp_path, 'rb') as f:
                    xpt_content = f.read()
                
                logger.info(f"Generated XPT file with pyreadstat: {len(xpt_content)} bytes")
                return xpt_content
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Error in pyreadstat XPT generation: {e}", exc_info=True)
            raise

    def _generate_xpt_with_pandas(self, df: pd.DataFrame, domain_code: str) -> Optional[bytes]:
        """Generate XPT using pandas - alternative method"""
        import tempfile
        import os
        
        try:
            # Prepare DataFrame for SAS format
            df_sas = self._prepare_dataframe_for_sas(df, domain_code)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.xpt', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            try:
                # Use pandas to_stata as intermediate step for better SAS compatibility
                # First convert to Stata format to ensure proper data type handling
                stata_path = temp_path.replace('.xpt', '.dta')
                
                # Prepare for Stata (which has similar restrictions to SAS)
                df_stata = df_sas.copy()
                
                # Convert string columns and handle encoding
                for col in df_stata.columns:
                    if df_stata[col].dtype == 'object':
                        # Ensure strings are properly encoded and not too long
                        df_stata[col] = df_stata[col].astype(str).str.encode('utf-8', errors='ignore').str.decode('utf-8')
                        df_stata[col] = df_stata[col].str[:244]  # Stata string limit
                
                # Write to Stata first (this ensures proper formatting)
                df_stata.to_stata(
                    stata_path,
                    write_index=False,
                    data_label=f"{domain_code} Domain Data",
                    variable_labels={col: col.replace('_', ' ').title() for col in df_stata.columns}
                )
                
                # Now use pandas to write XPT
                df_sas.to_xport(temp_path, table_name=domain_code.upper()[:8])
                
                # Read the generated file
                with open(temp_path, 'rb') as f:
                    xpt_content = f.read()
                
                logger.info(f"Generated XPT file with pandas: {len(xpt_content)} bytes")
                return xpt_content
                
            finally:
                # Clean up temporary files
                for path in [temp_path, temp_path.replace('.xpt', '.dta')]:
                    if os.path.exists(path):
                        os.unlink(path)
                        
        except Exception as e:
            logger.error(f"Error in pandas XPT generation: {e}", exc_info=True)
            raise

    def _prepare_dataframe_for_sas(self, df: pd.DataFrame, domain_code: str) -> pd.DataFrame:
        """Prepare DataFrame for SAS XPT format with proper data types and constraints"""
        df_prepared = df.copy()
        
        # Ensure DOMAIN column exists and is set correctly
        df_prepared['DOMAIN'] = domain_code.upper()
        
        # SAS XPT format constraints
        MAX_STRING_LENGTH = 200
        MAX_COLUMN_NAME_LENGTH = 8
        
        # Fix column names for SAS compatibility
        column_mapping = {}
        for col in df_prepared.columns:
            # SAS column names: max 8 chars, start with letter, alphanumeric + underscore only
            clean_col = col.upper()
            clean_col = ''.join(c for c in clean_col if c.isalnum() or c == '_')
            if clean_col and not clean_col[0].isalpha():
                clean_col = 'C' + clean_col  # Prefix with C if starts with number
            clean_col = clean_col[:MAX_COLUMN_NAME_LENGTH]
            
            # Ensure uniqueness
            base_col = clean_col
            counter = 1
            while clean_col in column_mapping.values():
                clean_col = base_col[:6] + str(counter).zfill(2)
                counter += 1
                
            column_mapping[col] = clean_col
        
        df_prepared = df_prepared.rename(columns=column_mapping)
        
        # Fix data types and values
        for col in df_prepared.columns:
            if df_prepared[col].dtype == 'object':
                # String columns
                df_prepared[col] = df_prepared[col].astype(str)
                df_prepared[col] = df_prepared[col].replace(['nan', 'None', 'NaN'], '')
                df_prepared[col] = df_prepared[col].str[:MAX_STRING_LENGTH]
                # Remove any problematic characters
                df_prepared[col] = df_prepared[col].str.replace(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', regex=True)
            else:
                # Numeric columns - convert to float64 (SAS numeric type)
                df_prepared[col] = pd.to_numeric(df_prepared[col], errors='coerce')
                df_prepared[col] = df_prepared[col].astype('float64')
        
        # Fill NaN values appropriately
        for col in df_prepared.columns:
            if df_prepared[col].dtype == 'object':
                df_prepared[col] = df_prepared[col].fillna('')
            else:
                df_prepared[col] = df_prepared[col].fillna(0)
        
        # Ensure required CDISC columns are present and in correct order
        required_cols = ['STUDYID', 'DOMAIN', 'USUBJID']
        existing_cols = [col for col in required_cols if col in df_prepared.columns]
        other_cols = [col for col in df_prepared.columns if col not in required_cols]
        
        # Reorder columns: required first, then others
        final_cols = existing_cols + sorted(other_cols)
        df_prepared = df_prepared[final_cols]
        
        logger.debug(f"Prepared DataFrame for SAS: {len(df_prepared)} rows, {len(df_prepared.columns)} columns")
        logger.debug(f"Final columns: {list(df_prepared.columns)}")
        logger.debug(f"Data types: {df_prepared.dtypes.to_dict()}")
        
        return df_prepared



# For backward compatibility, create an alias
ExtractionPipeline = SimpleExtractionPipeline