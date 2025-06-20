# extraction/utils.py
import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re
import io

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

class DataValidator:
    """Utility class for validating extracted SEND data"""
    
    @staticmethod
    def validate_send_format(df: pd.DataFrame, domain: str) -> Dict[str, Any]:
        """Validate DataFrame against SEND format requirements"""
        errors = []
        warnings = []
        
        # Check required columns
        required_cols = ["STUDYID", "DOMAIN", "USUBJID"]
        domain_seq_col = f"{domain}SEQ"
        
        if domain_seq_col not in required_cols:
            required_cols.append(domain_seq_col)
        
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        
        # Validate USUBJID format
        if 'USUBJID' in df.columns:
            invalid_usubjid = df[~df['USUBJID'].astype(str).str.match(r'^\d+-\d+$')]
            if not invalid_usubjid.empty:
                errors.append(f"Invalid USUBJID format in {len(invalid_usubjid)} records")
        
        # Check sequence numbers
        if domain_seq_col in df.columns and 'USUBJID' in df.columns:
            for usubjid in df['USUBJID'].unique():
                subject_data = df[df['USUBJID'] == usubjid]
                seq_values = subject_data[domain_seq_col].dropna()
                
                # Check for duplicates
                if len(seq_values) != len(seq_values.unique()):
                    errors.append(f"Duplicate sequence numbers for {usubjid}")
                
                # Check for sequential numbering
                if not seq_values.empty:
                    expected_seq = list(range(1, len(seq_values) + 1))
                    actual_seq = sorted(seq_values.astype(int))
                    if actual_seq != expected_seq:
                        warnings.append(f"Non-sequential sequence numbers for {usubjid}")
        
        # Check date formats
        date_columns = [col for col in df.columns if col.endswith('DTC')]
        for col in date_columns:
            if col in df.columns:
                invalid_dates = df[~df[col].astype(str).str.match(r'^\d{4}-\d{2}-\d{2}$|^$')]
                if not invalid_dates.empty:
                    warnings.append(f"Invalid date format in {col}: {len(invalid_dates)} records")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'record_count': len(df),
            'column_count': len(df.columns)
        }

class ExtractionCache:
    """Cache management for extraction operations"""
    
    @staticmethod
    def get_extraction_status(study_id: int, domain_code: str) -> Optional[str]:
        """Get cached extraction status"""
        cache_key = f"extraction_status_{study_id}_{domain_code}"
        return cache.get(cache_key)
    
    @staticmethod
    def set_extraction_status(study_id: int, domain_code: str, status: str, timeout: int = 3600):
        """Set extraction status in cache"""
        cache_key = f"extraction_status_{study_id}_{domain_code}"
        cache.set(cache_key, status, timeout)
    
    @staticmethod
    def clear_extraction_status(study_id: int, domain_code: str):
        """Clear extraction status from cache"""
        cache_key = f"extraction_status_{study_id}_{domain_code}"
        cache.delete(cache_key)

class TextProcessor:
    """Utility class for processing extracted text"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text for better AI processing"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page headers/footers patterns
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'Study No\.: \d+-\d+', '', text)
        
        # Clean up table formatting artifacts
        text = re.sub(r'-{3,}', '---', text)  # Standardize table borders
        text = re.sub(r'\.{3,}', '...', text)  # Standardize dot leaders
        
        return text.strip()
    
    @staticmethod
    def extract_tables(text: str) -> List[str]:
        """Extract table-like structures from text"""
        tables = []
        lines = text.split('\n')
        
        current_table = []
        in_table = False
        
        for line in lines:
            line = line.strip()
            
            # Detect table start (lines with multiple columns)
            if not in_table and ('|' in line or len(line.split()) > 3):
                in_table = True
                current_table = [line]
            elif in_table:
                if line and (len(line.split()) > 2 or '|' in line):
                    current_table.append(line)
                else:
                    # End of table
                    if len(current_table) > 2:  # At least header + 2 rows
                        tables.append('\n'.join(current_table))
                    current_table = []
                    in_table = False
        
        # Don't forget the last table
        if current_table and len(current_table) > 2:
            tables.append('\n'.join(current_table))
        
        return tables

class CSVProcessor:
    """Utility class for processing CSV data"""
    
    @staticmethod
    def clean_csv_response(csv_text: str) -> str:
        """Clean CSV response from AI models"""
        if not csv_text:
            return ""
        
        # Remove markdown code blocks
        csv_text = re.sub(r'```(?:csv)?\s*', '', csv_text)
        csv_text = re.sub(r'```\s*', '', csv_text)
        
        # Remove explanatory text before/after CSV
        lines = csv_text.split('\n')
        csv_lines = []
        found_header = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for CSV header (typically starts with STUDYID)
            if not found_header and line.upper().startswith('STUDYID'):
                found_header = True
                csv_lines.append(line)
            elif found_header and ',' in line:
                # Continue collecting CSV lines
                csv_lines.append(line)
            elif found_header and not ',' in line:
                # Likely end of CSV data
                break
        
        return '\n'.join(csv_lines)
    
    @staticmethod
    def parse_csv_safely(csv_text: str) -> Optional[pd.DataFrame]:
        """Safely parse CSV text into DataFrame"""
        try:
            if not csv_text.strip():
                return None
            
            # Try to parse with pandas
            df = pd.read_csv(io.StringIO(csv_text), skipinitialspace=True)
            
            # Basic validation
            if df.empty or len(df.columns) < 3:
                return None
            
            return df
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
            return None

class FileGenerator:
    """Utility class for generating various file formats"""
    
    @staticmethod
    def generate_sas_transport_file(df: pd.DataFrame, domain: str) -> bytes:
        """Generate SAS Transport (XPT) file from DataFrame"""
        try:
            # This is a simplified implementation
            # In production, you would use a proper SAS library like pyreadstat
            
            # For now, return CSV as bytes (placeholder)
            csv_content = df.to_csv(index=False)
            return csv_content.encode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating XPT file: {e}")
            return b""
    
    @staticmethod
    def generate_define_xml_snippet(domain: str, df: pd.DataFrame) -> str:
        """Generate define.xml snippet for a domain"""
        variables = []
        
        for col in df.columns:
            var_type = "text" if df[col].dtype == 'object' else "integer"
            max_length = df[col].astype(str).str.len().max() if not df.empty else 200
            
            variables.append(f"""
        <ItemDef OID="IT.{domain}.{col}" Name="{col}" DataType="{var_type}" Length="{max_length}">
            <Description>
                <TranslatedText xml:lang="en">{col}</TranslatedText>
            </Description>
        </ItemDef>""")
        
        return ''.join(variables)

class ProgressTracker:
    """Track extraction progress across multiple operations"""
    
    def __init__(self, study_id: int, total_domains: int):
        self.study_id = study_id
        self.total_domains = total_domains
        self.completed_domains = 0
        self.cache_key = f"extraction_progress_{study_id}"
    
    def update_progress(self, domain_code: str, status: str, details: Dict = None):
        """Update progress for a domain"""
        progress_data = cache.get(self.cache_key, {})
        
        progress_data[domain_code] = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        # Update completed count
        self.completed_domains = sum(
            1 for d in progress_data.values() 
            if d['status'] in ['completed', 'failed']
        )
        
        progress_data['_meta'] = {
            'total_domains': self.total_domains,
            'completed_domains': self.completed_domains,
            'progress_percentage': (self.completed_domains / self.total_domains) * 100
        }
        
        cache.set(self.cache_key, progress_data, 7200)  # 2 hours
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress"""
        return cache.get(self.cache_key, {})
    
    def clear_progress(self):
        """Clear progress tracking"""
        cache.delete(self.cache_key)
