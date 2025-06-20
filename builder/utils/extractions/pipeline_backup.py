# extraction/pipeline.py
import logging
import io
from io import StringIO
import pandas as pd
from typing import Dict, List, Any, Optional, TypedDict
from dataclasses import dataclass
from datetime import datetime

# from langchain.schema import BaseLanguageModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from django.core.files.base import ContentFile
from django.db import transaction

from builder.models import Study, DetectedDomain, StudyContent, ExtractedDomain, FDAFile
from ..ai_model.config import ai_config
from .prompts import ExtractionPrompts
from builder.utils.send_utils import get_required_columns
from .send_validator import post_process_domain_data

logger = logging.getLogger(__name__)

class ExtractionState(TypedDict):
    """State for the extraction workflow"""
    study_id: int
    domain_code: str
    pages: List[int]
    current_page_index: int
    extracted_chunks: List[str]
    final_data: Optional[pd.DataFrame]
    errors: List[str]
    status: str
    metadata: Dict[str, Any]
    retry_count: int
    max_retries: int

@dataclass
class ExtractionConfig:
    """Configuration for extraction pipeline"""
    chunk_size: int = 6000
    max_retries: int = 3
    validate_results: bool = True
    save_intermediate: bool = False

class ExtractionPipeline:
    """Main extraction pipeline using LangGraph"""
    
    def __init__(self, config: ExtractionConfig = None):
        self.config = config or ExtractionConfig()
        self.llm = None
        self.prompts = ExtractionPrompts()
        self.output_parser = StrOutputParser()
        self.memory = MemorySaver()
        self._build_workflow()
    
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
    
    def _build_workflow(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(ExtractionState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_extraction)
        workflow.add_node("load_page_content", self._load_page_content)
        workflow.add_node("extract_from_page", self._extract_from_page)
        workflow.add_node("validate_chunk", self._validate_chunk)
        workflow.add_node("combine_results", self._combine_results)
        workflow.add_node("finalize_data", self._finalize_data)
        workflow.add_node("save_results", self._save_results)
        workflow.add_node("handle_error", self._handle_error)
        
        # Define workflow edges
        workflow.set_entry_point("initialize")
        
        workflow.add_edge("initialize", "load_page_content")
        workflow.add_edge("load_page_content", "extract_from_page")
        workflow.add_edge("extract_from_page", "validate_chunk")
        
        # FIXED: Add conditional edge from validate_chunk
        workflow.add_conditional_edges(
            "validate_chunk",
            self._decide_next_step,  # NEW METHOD
            {
                "continue": "load_page_content",
                "combine": "combine_results", 
                "error": "handle_error",
                "retry": "extract_from_page"  # Add retry option
            }
        )
        
        workflow.add_edge("combine_results", "finalize_data")
        workflow.add_edge("finalize_data", "save_results")
        workflow.add_edge("save_results", END)
        workflow.add_edge("handle_error", END)
        
        self.workflow = workflow.compile(checkpointer=self.memory)
    
    def extract_domain(self, study_id: int, domain_code: str) -> Dict[str, Any]:
        """Main entry point for domain extraction"""
        if not self._initialize_llm():
            return {"success": False, "error": "Failed to initialize LLM"}
        
        # Get detected domain info
        try:
            detected_domain = DetectedDomain.objects.get(
                study_id=study_id, 
                domain__code=domain_code
            )
            pages = detected_domain.page
        except DetectedDomain.DoesNotExist:
            return {"success": False, "error": f"Domain {domain_code} not detected for study {study_id}"}
        
        # Initialize state
        initial_state = ExtractionState(
            study_id=study_id,
            domain_code=domain_code,
            pages=pages,
            current_page_index=0,
            extracted_chunks=[],
            final_data=None,
            errors=[],
            status="initialized",
            metadata={
                "start_time": datetime.now().isoformat(),
                "model_config": ai_config.get_model_config('CHAT')
            },
            retry_count=0,      # ADD THIS LINE
            max_retries=3       # ADD THIS LINE
        )
        
        # Run workflow
        thread_id = f"extraction_{study_id}_{domain_code}_{datetime.now().timestamp()}"
        
        # ADD WORKFLOW CONFIG
        workflow_config = {
            "recursion_limit": 100,
            "configurable": {"thread_id": thread_id}
        }
        
        try:
            result = self.workflow.invoke(
                initial_state,
                config=workflow_config
            )
            
            return {
                "success": result["status"] == "completed",
                "data": result.get("final_data"),
                "errors": result.get("errors", []),
                "metadata": result.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _initialize_extraction(self, state: ExtractionState) -> ExtractionState:
        """Initialize the extraction process"""
        logger.info(f"Starting extraction for study {state['study_id']}, domain {state['domain_code']}")
        state["status"] = "extracting"
        state["metadata"]["pages_total"] = len(state["pages"])
        return state
    
    def _load_page_content(self, state: ExtractionState) -> ExtractionState:
        """Load content for the current page"""
        try:
            current_page = state["pages"][state["current_page_index"]]
            
            # Get page content from StudyContent
            content_obj = StudyContent.objects.get(
                study_id=state["study_id"],
                page=current_page
            )
            
            state["metadata"]["current_page"] = current_page
            state["metadata"]["current_content"] = content_obj.content
            
            logger.info(f"Loaded content for page {current_page} ({len(content_obj.content)} chars)")
            
        except StudyContent.DoesNotExist:
            error_msg = f"Content not found for page {current_page}"
            state["errors"].append(error_msg)
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"Error loading page content: {str(e)}"
            state["errors"].append(error_msg)
            logger.error(error_msg)
        
        return state
    
    def _extract_from_page(self, state: ExtractionState) -> ExtractionState:
        """Extract data from the current page"""
        # Add circuit breaker - track total extractions
        total_extractions = state["metadata"].get("total_extractions", 0)
        if total_extractions > len(state["pages"]) * 5:  # Max 5 attempts per page
            logger.error("Circuit breaker: Too many extraction attempts")
            state["errors"].append("Too many extraction attempts - stopping")
            state["status"] = "failed"
            return state
        
        state["metadata"]["total_extractions"] = total_extractions + 1
        
        try:
            content = state["metadata"].get("current_content", "")
            if not content:
                state["errors"].append("No content to extract from")
                return state
            
            # Create extraction prompt
            chunk_info = {
                "current": state["current_page_index"] + 1,
                "total": len(state["pages"])
            }

            prompt = self.prompts.get_domain_extraction_prompt(
                state["domain_code"], 
                content, 
                chunk_info
            )
            
            # Create prompt template
            prompt_template = PromptTemplate(
                template="{system_prompt}\n\n{extraction_prompt}",
                input_variables=["system_prompt", "extraction_prompt"]
            )

            # Create chain using LCEL
            extraction_chain = prompt_template | self.llm | StrOutputParser()

            # Extract data
            response = extraction_chain.invoke({
                "system_prompt": self.prompts.get_system_prompt(),
                "extraction_prompt": prompt
            })
            
            # Clean and store the extracted data
            cleaned_response = self._clean_csv_response(response)
            if cleaned_response:
                state["extracted_chunks"].append(cleaned_response)
                logger.info(f"Extracted data from page {state['metadata']['current_page']}")
            else:
                error_msg = f"No valid data extracted from page {state['metadata']['current_page']}"
                state["errors"].append(error_msg)
                logger.warning(error_msg)
            
        except Exception as e:
            error_msg = f"Error extracting from page: {str(e)}"
            state["errors"].append(error_msg)
            logger.error(error_msg)
        
        return state
    
    def _validate_chunk(self, state: ExtractionState) -> ExtractionState:
        """Validate extracted chunk data"""
        
        current_retries = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        current_page = state.get("current_page_index", 0)
        
        # Store last processed page to detect page changes
        last_page = state["metadata"].get("last_processed_page", -1)
        
        # Reset retry count if we moved to a new page
        if current_page != last_page:
            state["retry_count"] = 0
            state["metadata"]["last_processed_page"] = current_page
            current_retries = 0
            logger.info(f"Reset retry count for new page {current_page}")
        
        if current_retries >= max_retries:
            logger.warning(f"Max retries ({max_retries}) reached for page {current_page}. Moving to next page.")
            state["status"] = "chunk_valid"  # Force acceptance to move forward
            return state
        
        # Rest of your validation logic remains the same...
        if not state.get("extracted_chunks"):
            logger.error("No chunks to validate")
            state["retry_count"] = current_retries + 1
            state["status"] = "retry_extraction"  # Changed from "failed"
            return state
        
        # Get the latest chunk
        latest_chunk = state["extracted_chunks"][-1]
        
        try:
            # Parse CSV
            df = pd.read_csv(StringIO(latest_chunk))
            
            if df.empty:
                logger.warning(f"Empty dataframe in chunk for page {current_page}")
                state["retry_count"] = current_retries + 1
                state["status"] = "retry_extraction"
                return state
            
            # Your existing column validation logic...
            required_cols = get_required_columns(state["domain_code"])
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"Missing columns in chunk: {missing_cols}")
                
                # Auto-fix missing columns instead of retrying
                for col in missing_cols:
                    if col.endswith('ORRES'):
                        df[col] = ""
                    elif col.endswith('ORRESU'):
                        df[col] = ""
                    elif col.endswith('SEQ'):
                        df[col] = range(1, len(df) + 1)
                    elif col == 'DOMAIN':
                        df[col] = state["domain_code"]
                    else:
                        df[col] = ""
                
                # Update the chunk with corrected data
                corrected_csv = df.to_csv(index=False)
                state["extracted_chunks"][-1] = corrected_csv
                logger.info(f"Auto-fixed missing columns: {missing_cols}")
            
            # Mark as valid - DO NOT reset retry count here (it's handled above)
            state["status"] = "chunk_valid"
            return state
            
        except Exception as e:
            logger.error(f"Validation error for page {current_page}: {str(e)}")
            state["retry_count"] = current_retries + 1
            state["status"] = "retry_extraction"
            return state
    def _combine_results(self, state: ExtractionState) -> ExtractionState:
        """Combine results from all pages"""
        try:
            if not state["extracted_chunks"]:
                state["errors"].append("No data chunks to combine")
                return state
            
            # Use LLM to intelligently combine chunks if multiple
            if len(state["extracted_chunks"]) > 1:
                combine_prompt = self.prompts.get_chunk_combination_prompt(
                    state["domain_code"], 
                    state["extracted_chunks"]
                )
                
                # Create prompt template
                combine_prompt_template = PromptTemplate(
                    template="{combine_prompt}",
                    input_variables=["combine_prompt"]
                )

                # Create chain using LCEL
                combination_chain = combine_prompt_template | self.llm | StrOutputParser()

                combined_data = combination_chain.invoke({"combine_prompt": combine_prompt})
                combined_data = self._clean_csv_response(combined_data)
            else:
                combined_data = state["extracted_chunks"][0]
            
            # Parse to DataFrame
            if combined_data:
                df = pd.read_csv(pd.StringIO(combined_data))
                state["final_data"] = df
                logger.info(f"Combined data: {len(df)} records")
            else:
                state["errors"].append("Failed to combine chunk data")
            
        except Exception as e:
            error_msg = f"Error combining results: {str(e)}"
            state["errors"].append(error_msg)
            logger.error(error_msg)
        
        return state
    
    def _finalize_data(self, state: ExtractionState) -> ExtractionState:
        """Finalize and post-process the extracted data"""
        try:
            if state["final_data"] is None:
                state["errors"].append("No final data to process")
                return state
            
            # Post-process using existing utilities
            processed_df = post_process_domain_data(
                state["final_data"], 
                state["domain_code"]
            )
            
            state["final_data"] = processed_df
            state["metadata"]["final_record_count"] = len(processed_df)
            
            logger.info(f"Finalized {len(processed_df)} records for {state['domain_code']}")
            
        except Exception as e:
            error_msg = f"Error finalizing data: {str(e)}"
            state["errors"].append(error_msg)
            logger.error(error_msg)
        
        return state
    
    def _save_results(self, state: ExtractionState) -> ExtractionState:
        """Save the extracted data to database"""
        try:
            if state["final_data"] is None or state["final_data"].empty:
                state["errors"].append("No data to save")
                return state
            
            with transaction.atomic():
                # Get or create ExtractedDomain
                extracted_domain, created = ExtractedDomain.objects.get_or_create(
                    study_id=state["study_id"],
                    domain__code=state["domain_code"],
                    defaults={
                        'content': state["final_data"].to_dict('records')
                    }
                )
                
                if not created:
                    extracted_domain.content = state["final_data"].to_dict('records')
                    extracted_domain.save()
                
                # Generate and save XPT file
                xpt_content = self._generate_xpt_file(state["final_data"], state["domain_code"])
                if xpt_content:
                    xpt_file = ContentFile(
                        xpt_content, 
                        name=f"{state['domain_code']}.xpt"
                    )
                    extracted_domain.xpt_file.save(
                        f"{state['domain_code']}.xpt", 
                        xpt_file, 
                        save=True
                    )
                
                state["status"] = "completed"
                state["metadata"]["extracted_domain_id"] = extracted_domain.id
                
                logger.info(f"Saved extraction results for {state['domain_code']}")
                
        except Exception as e:
            error_msg = f"Error saving results: {str(e)}"
            state["errors"].append(error_msg)
            logger.error(error_msg)
            state["status"] = "failed"
        
        return state
    
    def _handle_error(self, state: ExtractionState) -> ExtractionState:
        """Handle errors in the workflow"""
        state["status"] = "failed"
        logger.error(f"Extraction failed for {state['domain_code']}: {state['errors']}")
        return state
    
    def _clean_csv_response(self, response: str) -> str:
        """Clean the LLM response to extract valid CSV data"""
        import re
        
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
            if not found_header and line.upper().startswith('STUDYID'):
                found_header = True
                csv_lines.append(line)
            elif found_header and ',' in line:
                csv_lines.append(line)
        
        return '\n'.join(csv_lines) if csv_lines else ""
    
    def _generate_xpt_file(self, df: pd.DataFrame, domain_code: str) -> Optional[bytes]:
        """Generate XPT file from DataFrame"""
        try:
            # This is a placeholder - implement actual XPT generation
            # You might want to use pyreadstat or similar library
            import io
            buffer = io.BytesIO()
            # df.to_sas(buffer, format='xport')  # Example with pandas
            # return buffer.getvalue()
            
            # For now, return CSV as bytes as placeholder
            return df.to_csv(index=False).encode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating XPT file: {e}")
            return None

    def _decide_next_step(self, state: ExtractionState) -> str:
        """Decide the next step after validation"""
        current_retries = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        status = state.get("status", "")
        
        logger.info(f"Decision point: status={status}, retries={current_retries}/{max_retries}, page={state['current_page_index']}/{len(state['pages'])}")
        
        # Force completion if max retries reached
        if current_retries >= max_retries:
            logger.warning("Max retries reached - combining results")
            return "combine"
        
        # Handle errors - but don't loop endlessly
        if len(state["errors"]) > 5:  # ADD THIS CHECK
            logger.warning("Too many errors - combining results")
            return "combine"
        
        # Handle retry extraction - but limit retries per page
        if status == "retry_extraction":
            if current_retries < max_retries:
                logger.info("Retrying extraction for current page")
                return "retry"
            else:
                # Skip this page and move to next
                state["current_page_index"] += 1
                logger.warning(f"Skipping page after max retries, moving to page {state['current_page_index'] + 1}")
                
        # Handle successful validation
        if status == "chunk_valid":
            # Move to next page
            state["current_page_index"] += 1
            
        # Check if we have more pages to process
        if state["current_page_index"] < len(state["pages"]):
            logger.info(f"Moving to page {state['current_page_index'] + 1}")
            return "continue"
        else:
            logger.info("All pages processed - combining results")
            return "combine"