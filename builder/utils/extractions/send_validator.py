# builder/utils/extractions/send_validator.py - FIXED VERSION
# Changes are marked with # FIXED comments

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

from builder.utils.send_utils import get_required_columns,get_column_description

logger = logging.getLogger(__name__)

def post_process_domain_data(df: pd.DataFrame, domain: str, study: object = None) -> pd.DataFrame:
    """
    Post-process extracted domain data to ensure SEND compliance
    
    Args:
        df (pd.DataFrame): Raw extracted data
        domain (str): SEND domain code (e.g., 'DM', 'CL', 'BW')
        study (object): Study object (optional)
        
    Returns:
        pd.DataFrame: Post-processed, SEND-compliant data
    """
    if df is None or df.empty:
        logger.warning(f"Empty dataframe provided for domain {domain}")
        return pd.DataFrame()
    
    try:
        logger.info(f"Post-processing {domain} domain with {len(df)} records")
        
        # Create a copy to avoid modifying original
        processed_df = df.copy()
        
        # 1. Standardize column names
        processed_df = _standardize_column_names(processed_df, domain)
        
        # 2. Ensure required columns exist
        processed_df = _ensure_required_columns(processed_df, domain, study)
        
        # 3. Normalize data types
        processed_df = _normalize_data_types(processed_df, domain)
        
        # 4. Clean and validate data values
        processed_df = _clean_data_values(processed_df, domain)
        
        # 5. Apply domain-specific transformations
        processed_df = _apply_domain_transformations(processed_df, domain)
        
        # 6. Normalize sequence numbers
        processed_df = _normalize_sequence_numbers(processed_df, domain)
        
        # 7. Apply controlled terminology
        processed_df = _apply_controlled_terminology(processed_df, domain)
        
        # 8. FIXED: Validate and fix cross-references with study context
        processed_df = _validate_cross_references(processed_df, domain, study)
        
        # 9. Final data validation and cleanup
        processed_df = _final_cleanup(processed_df, domain)
        
        # 10. Sort data appropriately
        processed_df = _sort_domain_data(processed_df, domain)
        
        logger.info(f"Post-processing complete for {domain}: {len(processed_df)} records")
        return processed_df
        
    except Exception as e:
        logger.error(f"Error post-processing {domain} domain: {e}", exc_info=True)
        return df  # Return original data if processing fails

def _get_default_value(column: str, domain: str, df: pd.DataFrame, study=None) -> Any:
    """Get appropriate default value for missing column"""
    
    # FIXED: Use study object as primary source for STUDYID
    if column == 'STUDYID':
        if study and hasattr(study, 'study_number'):
            return study.study_number
        elif study and hasattr(study, 'get_standardized_study_id'):
            return study.get_standardized_study_id()
        elif 'USUBJID' in df.columns:
            # FIXED: Better logic to extract STUDYID from USUBJID
            sample_usubjid = df['USUBJID'].dropna().iloc[0] if not df['USUBJID'].dropna().empty else ''
            if sample_usubjid:
                # Use regex to extract proper STUDYID format (XXXX-XXXX)
                match = re.search(r'\b(\d{4}-\d{4})\b', str(sample_usubjid))
                if match:
                    return match.group(1)
            return 'UNKNOWN'
        else:
            return 'UNKNOWN'
    
    # Use study information for RFSTDTC (Reference Start Date/Time)
    if column == 'RFSTDTC' and study and hasattr(study, 'start_date'):
        if study.start_date:
            return study.start_date.strftime('%Y-%m-%d')
        return ''
    
    # Use study information for SPECIES
    if column == 'SPECIES' and study and hasattr(study, 'species'):
        if study.species:
            return study.species.upper()
        return 'RAT'
    
    # Domain-specific defaults
    defaults = {
        'STUDYID': study.study_number if study and hasattr(study, 'study_number') else 'UNKNOWN',
        'DOMAIN': domain,
        'USUBJID': '',
        'SUBJID': '',
        'RFSTDTC': study.start_date.strftime('%Y-%m-%d') if study and hasattr(study, 'start_date') and study.start_date else '',
        'SPECIES': study.species.upper() if study and hasattr(study, 'species') and study.species else 'RAT',
        'SEX': '',
        'STRAIN': '',
        'ARM': '',
        'ARMCD': '',
        f'{domain}SEQ': 1,
        f'{domain}TESTCD': f'{domain}',
        f'{domain}TEST': f'{domain} Test',
        f'{domain}ORRES': '',
        f'{domain}ORRESU': '',
        f'{domain}STRESC': '',
        f'{domain}DTC': '',
        f'{domain}DY': '',
        'VISITDY': '',
        'EXTRT': 'Test Article',
        'EXROUTE': 'ORAL',
        'LBSPEC': 'SERUM',
        'LBBLFL': 'N',
        'MASTRESC': 'NORMAL',
        'MISTRESC': 'NORMAL',
        'PCSPEC': 'PLASMA',
        'PCTESTCD': 'PARENT',
        'PCTEST': 'Parent Compound',
        'PCORRESU': 'ng/mL',
        'PCSTRESU': 'ng/mL',
        'DDTESTCD': 'NECROPSY',
        'DDTEST': 'Cause of Death',
        'DDEVAL': 'PATHOLOGIST',
        'DDCAT': 'PRIMARY',
        'DDSTRESC': 'SCHEDULED SACRIFICE',
    }
    
    return defaults.get(column, '')

def _validate_cross_references(df: pd.DataFrame, domain: str, study=None) -> pd.DataFrame:
    """FIXED: Validate and fix cross-references between variables with study context"""
    
    # Ensure DOMAIN matches the domain parameter
    if 'DOMAIN' in df.columns:
        df['DOMAIN'] = domain
    
    # FIXED: Use study object as authoritative source for STUDYID
    if study and hasattr(study, 'study_number'):
        authoritative_studyid = study.study_number
        logger.info(f"Using authoritative STUDYID from study: {authoritative_studyid}")
        
        # Set STUDYID consistently across all records
        if 'STUDYID' in df.columns:
            df['STUDYID'] = authoritative_studyid
        
        # FIXED: Fix USUBJID format using study methods if available
        if 'USUBJID' in df.columns:
            for idx, row in df.iterrows():
                usubjid = str(row['USUBJID']).strip()
                
                if usubjid and usubjid not in ['nan', 'None', '']:
                    try:
                        # Use study's validation method if available
                        if hasattr(study, 'validate_usubjid'):
                            corrected_usubjid = study.validate_usubjid(usubjid)
                            df.at[idx, 'USUBJID'] = corrected_usubjid
                        elif hasattr(study, 'generate_usubjid'):
                            # Extract subject ID and regenerate
                            subject_id = _extract_subject_id_from_usubjid(usubjid, authoritative_studyid)
                            if subject_id:
                                corrected_usubjid = study.generate_usubjid(subject_id)
                                df.at[idx, 'USUBJID'] = corrected_usubjid
                        else:
                            # Fallback method
                            corrected_usubjid = _fix_usubjid_format(usubjid, authoritative_studyid)
                            df.at[idx, 'USUBJID'] = corrected_usubjid
                            
                        logger.debug(f"Fixed USUBJID: {usubjid} -> {df.at[idx, 'USUBJID']}")
                        
                    except Exception as e:
                        logger.warning(f"Could not fix USUBJID {usubjid}: {e}")
                        # Set a default if all else fails
                        df.at[idx, 'USUBJID'] = f"{authoritative_studyid}-{str(idx+1).zfill(3)}"
    
    # Generate SUBJID from USUBJID if missing
    if 'SUBJID' not in df.columns and 'USUBJID' in df.columns:
        df['SUBJID'] = df['USUBJID'].apply(lambda x: _extract_subject_id_from_usubjid(str(x)))
    
    return df

def _extract_subject_id_from_usubjid(usubjid: str, expected_studyid: str = None) -> str:
    """
    FIXED: Extract subject ID from USUBJID with better logic
    
    Args:
        usubjid (str): The USUBJID to parse
        expected_studyid (str): Expected STUDYID format for validation
        
    Returns:
        str: Extracted subject ID
    """
    if not usubjid or str(usubjid).strip() in ['nan', 'None', '']:
        return ''
    
    usubjid_str = str(usubjid).strip()
    
    # If we have expected STUDYID, use it to extract subject ID
    if expected_studyid:
        expected_prefix = f"{expected_studyid}-"
        if usubjid_str.startswith(expected_prefix):
            return usubjid_str[len(expected_prefix):]
    
    # Split by dashes and find the subject part
    parts = usubjid_str.split('-')
    
    if len(parts) >= 3:
        # Format like 1124-8751-003 -> subject is 003
        # Or 1124-8751-003-001 -> subject is 001 (last part)
        return parts[-1]
    elif len(parts) == 2:
        # Format like 1124-8751-003 where the whole thing was treated as STUDYID-SUBJID
        # Check if second part looks like a subject ID (numeric, short)
        if re.match(r'^\d{1,4}$', parts[1]):
            return parts[1]
    
    # Fallback: extract all digits and use last 3
    digits = re.findall(r'\d+', usubjid_str)
    if digits:
        return digits[-1].zfill(3)
    
    return '001'  # Default fallback

def _fix_usubjid_format(usubjid: str, studyid: str) -> str:
    """
    FIXED: Fix USUBJID format to be STUDYID-SUBJID
    
    Args:
        usubjid (str): Original USUBJID
        studyid (str): Correct STUDYID
        
    Returns:
        str: Fixed USUBJID
    """
    if not usubjid or str(usubjid).strip() in ['nan', 'None', '']:
        return f"{studyid}-001"
    
    usubjid_str = str(usubjid).strip()
    
    # Extract subject ID
    subject_id = _extract_subject_id_from_usubjid(usubjid_str, studyid)
    
    # Ensure subject ID is properly formatted (at least 3 digits)
    if subject_id.isdigit():
        subject_id = subject_id.zfill(3)
    
    return f"{studyid}-{subject_id}"

# Keep all other existing functions unchanged...
def _standardize_column_names(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Standardize column names to SEND conventions"""
    
    # Common column name mappings
    column_mappings = {
        # Common standardizations
        'study_id': 'STUDYID',
        'studyid': 'STUDYID',
        'subject_id': 'USUBJID',
        'subjectid': 'USUBJID',
        'usubjid': 'USUBJID',
        'domain': 'DOMAIN',
        
        # Domain-specific mappings
        'CL': {
            'sequence': 'CLSEQ',
            'seq': 'CLSEQ',
            'observation': 'CLTEST',
            'test': 'CLTEST',
            'result': 'CLORRES',
            'severity': 'CLSEV',
            'date': 'CLDTC',
            'day': 'CLDY'
        },
        'BW': {
            'sequence': 'BWSEQ',
            'seq': 'BWSEQ',
            'weight': 'BWORRES',
            'result': 'BWORRES',
            'unit': 'BWORRESU',
            'units': 'BWORRESU',
            'date': 'BWDTC',
            'day': 'BWDY'
        },
        'DM': {
            'subject': 'SUBJID',
            'sex': 'SEX',
            'species': 'SPECIES',
            'strain': 'STRAIN',
            'arm': 'ARM',
            'group': 'ARMCD'
        },
        'EX': {
            'sequence': 'EXSEQ',
            'treatment': 'EXTRT',
            'dose': 'EXDOSE',
            'route': 'EXROUTE',
            'start_date': 'EXSTDTC',
            'end_date': 'EXENDTC'
        },
        'PC': {
            'sequence': 'PCSEQ',
            'seq': 'PCSEQ',
            'test_code': 'PCTESTCD',
            'testcd': 'PCTESTCD',
            'test_name': 'PCTEST',
            'test': 'PCTEST',
            'result': 'PCORRES',
            'original_result': 'PCORRES',
            'unit': 'PCORRESU',
            'units': 'PCORRESU',
            'original_unit': 'PCORRESU',
            'specimen': 'PCSPEC',
            'spec': 'PCSPEC',
            'date': 'PCDTC',
            'collection_date': 'PCDTC',
            'day': 'PCDY',
            'study_day': 'PCDY',
            'standard_result': 'PCSTRESC',
            'standard_unit': 'PCSTRESU',
            'numeric_result': 'PCSTRESN'
        },
        'DD': {
            'sequence': 'DDSEQ',
            'seq': 'DDSEQ',
            'test_code': 'DDTESTCD',
            'testcd': 'DDTESTCD',
            'test_name': 'DDTEST',
            'test': 'DDTEST',
            'result': 'DDORRES',
            'original_result': 'DDORRES',
            'finding': 'DDORRES',
            'diagnosis': 'DDORRES',
            'cause': 'DDORRES',
            'cause_of_death': 'DDORRES',
            'standard_result': 'DDSTRESC',
            'standard_finding': 'DDSTRESC',
            'date': 'DDDTC',
            'death_date': 'DDDTC',
            'day': 'DDDY',
            'study_day': 'DDDY',
            'evaluator': 'DDEVAL',
            'pathologist': 'DDEVAL',
            'category': 'DDCAT',
            'subcategory': 'DDSCAT'
        },
    }
    
    # Apply general mappings
    df.columns = [column_mappings.get(col.lower(), col.upper()) for col in df.columns]
    
    # Apply domain-specific mappings
    if domain in column_mappings:
        domain_mapping = column_mappings[domain]
        df.columns = [domain_mapping.get(col.lower(), col) for col in df.columns]
    
    return df

def _ensure_required_columns(df: pd.DataFrame, domain: str, study=None) -> pd.DataFrame:
    """Ensure all required SEND columns are present"""
    
    required_cols = get_required_columns(domain)
    
    # Add missing columns with appropriate defaults
    for col in required_cols:
        if col not in df.columns:
            default_value = _get_default_value(col, domain, df, study)
            df[col] = default_value
            logger.info(f"Added missing column {col} with default value")
    
    return df

def _normalize_data_types(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Normalize data types according to SEND specifications"""
    
    # Define expected data types for common variables
    data_types = {
        # Character variables
        'STUDYID': 'str',
        'DOMAIN': 'str',
        'USUBJID': 'str',
        'SUBJID': 'str',
        'SPECIES': 'str',
        'SEX': 'str',
        'STRAIN': 'str',
        'ARM': 'str',
        'ARMCD': 'str',
        
        # Numeric variables (sequence numbers)
        f'{domain}SEQ': 'int',
        'VISITDY': 'int',
        f'{domain}DY': 'int',
        
        # Test codes and names
        f'{domain}TESTCD': 'str',
        f'{domain}TEST': 'str',
        
        # Results - could be numeric or character
        f'{domain}ORRES': 'str',  # Keep as string initially
        f'{domain}STRESC': 'str',
        
        # Units
        f'{domain}ORRESU': 'str',
        f'{domain}STRESU': 'str'
    }
    
    for col, dtype in data_types.items():
        if col in df.columns:
            try:
                if dtype == 'str':
                    df[col] = df[col].astype(str).replace(['nan', 'None', 'NaN'], '')
                elif dtype == 'int':
                    # Convert to numeric first, then to int, handling NaNs
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                elif dtype == 'float':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception as e:
                logger.warning(f"Could not convert {col} to {dtype}: {e}")
    
    return df

def _clean_data_values(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Clean and standardize data values"""
    
    # Clean string columns
    string_columns = df.select_dtypes(include=['object']).columns
    for col in string_columns:
        if col in df.columns:
            # Remove extra whitespace and standardize missing values
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace(['nan', 'None', 'NaN', 'null', 'NULL'], '')
    
    # Standardize date columns
    date_columns = [col for col in df.columns if col.endswith('DTC')]
    for col in date_columns:
        if col in df.columns:
            df[col] = _standardize_dates(df[col])
    
    # Clean numeric result columns
    numeric_result_cols = [col for col in df.columns if col.endswith('ORRES')]
    for col in numeric_result_cols:
        if col in df.columns:
            df[col] = _clean_numeric_values(df[col])
    
    return df

def _standardize_dates(series: pd.Series) -> pd.Series:
    """Standardize date formats to ISO 8601 (YYYY-MM-DD)"""
    
    def parse_date(date_str):
        if pd.isna(date_str) or date_str == '' or str(date_str).lower() in ['nan', 'none', 'null']:
            return ''
        
        date_str = str(date_str).strip()
        
        # Common date patterns
        patterns = [
            ('%Y-%m-%d', r'^\d{4}-\d{2}-\d{2}$'),  # 2023-01-15
            ('%d/%m/%Y', r'^\d{2}/\d{2}/\d{4}$'),   # 15/01/2023
            ('%m/%d/%Y', r'^\d{2}/\d{2}/\d{4}$'),   # 01/15/2023
            ('%d-%m-%Y', r'^\d{2}-\d{2}-\d{4}$'),   # 15-01-2023
            ('%m-%d-%Y', r'^\d{2}-\d{2}-\d{4}$'),   # 01-15-2023
            ('%Y%m%d', r'^\d{8}$'),                 # 20230115
            ('%d-%b-%Y', r'^\d{2}-[A-Za-z]{3}-\d{4}$'),  # 15-Jan-2023
        ]
        
        for fmt, pattern in patterns:
            if re.match(pattern, date_str):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        # If no pattern matches, return original
        return date_str
    
    return series.apply(parse_date)

def _clean_numeric_values(series: pd.Series) -> pd.Series:
    """Clean numeric values while preserving non-numeric results"""
    
    def clean_value(val):
        if pd.isna(val) or val == '' or str(val).lower() in ['nan', 'none', 'null']:
            return ''
        
        val_str = str(val).strip()
        
        # Try to convert to numeric
        try:
            # Remove common non-numeric characters
            cleaned = re.sub(r'[^\d\.\-\+eE]', '', val_str)
            if cleaned and cleaned not in ['.', '-', '+']:
                float_val = float(cleaned)
                # Return as integer if it's a whole number
                if float_val.is_integer():
                    return str(int(float_val))
                else:
                    return str(float_val)
        except (ValueError, AttributeError):
            pass
        
        # Return original if not numeric
        return val_str
    
    return series.apply(clean_value)

def _apply_domain_transformations(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Apply domain-specific transformations"""
    
    if domain == 'CL':
        df = _transform_clinical_observations(df)
    elif domain == 'BW':
        df = _transform_body_weights(df)
    elif domain == 'DM':
        df = _transform_demographics(df)
    elif domain == 'EX':
        df = _transform_exposure(df)
    elif domain == 'LB':
        df = _transform_lab_results(df)
    elif domain == 'MA':
        df = _transform_macro_findings(df)
    elif domain == 'MI':
        df = _transform_micro_findings(df)
    elif domain == 'CO':
        df = _transform_comments(df)
    elif domain == 'PC':
        df = _transform_pharmacokinetic_concentrations(df)
    elif domain == 'DD':
        df = _transform_death_diagnosis(df)
    
    return df

def _transform_clinical_observations(df: pd.DataFrame) -> pd.DataFrame:
    """Transform clinical observations data"""
    
    # Standardize test codes
    if 'CLTESTCD' not in df.columns and 'CLTEST' in df.columns:
        df['CLTESTCD'] = df['CLTEST'].apply(_generate_test_code)
    
    # Ensure CLSTRESC is populated
    if 'CLSTRESC' not in df.columns and 'CLORRES' in df.columns:
        df['CLSTRESC'] = df['CLORRES'].apply(_standardize_clinical_result)
    
    # Set default values for missing required fields
    if 'CLCAT' not in df.columns:
        df['CLCAT'] = 'GENERAL OBSERVATIONS'
    
    if 'CLLOC' not in df.columns:
        df['CLLOC'] = 'WHOLE BODY'
    
    return df

def _transform_body_weights(df: pd.DataFrame) -> pd.DataFrame:
    """Transform body weight data"""
    
    # Standardize test codes
    if 'BWTESTCD' not in df.columns:
        df['BWTESTCD'] = 'BW'
    
    if 'BWTEST' not in df.columns:
        df['BWTEST'] = 'Body Weight'
    
    # Standardize units
    if 'BWORRESU' not in df.columns:
        df['BWORRESU'] = 'g'  # Default to grams
    
    return df

def _transform_demographics(df: pd.DataFrame) -> pd.DataFrame:
    """Transform demographics data"""
    
    # Generate SUBJID from USUBJID if missing
    if 'SUBJID' not in df.columns and 'USUBJID' in df.columns:
        df['SUBJID'] = df['USUBJID'].apply(lambda x: str(x).split('-')[-1] if '-' in str(x) else str(x))
    
    # Set default species if not provided
    if 'SPECIES' in df.columns:
        df['SPECIES'] = df['SPECIES'].fillna('RAT').str.upper()
    
    return df

def _transform_exposure(df: pd.DataFrame) -> pd.DataFrame:
    """Transform exposure data"""
    
    # Set default route if not provided
    if 'EXROUTE' not in df.columns:
        df['EXROUTE'] = 'ORAL'
    
    # Set default frequency
    if 'EXDOSFRQ' not in df.columns:
        df['EXDOSFRQ'] = 'QD'  # Once daily
    
    return df

def _transform_lab_results(df: pd.DataFrame) -> pd.DataFrame:
    """Transform laboratory results data"""
    
    # Set default specimen type
    if 'LBSPEC' not in df.columns:
        df['LBSPEC'] = 'SERUM'
    
    # Set baseline flag
    if 'LBBLFL' not in df.columns:
        df['LBBLFL'] = 'N'
    
    return df

def _transform_macro_findings(df: pd.DataFrame) -> pd.DataFrame:
    """Transform macroscopic findings data"""
    
    # Standardize result codes
    if 'MASTRESC' not in df.columns and 'MAORRES' in df.columns:
        df['MASTRESC'] = df['MAORRES'].apply(_standardize_finding_result)
    
    return df

def _transform_micro_findings(df: pd.DataFrame) -> pd.DataFrame:
    """Transform microscopic findings data"""
    
    # Standardize result codes
    if 'MISTRESC' not in df.columns and 'MIORRES' in df.columns:
        df['MISTRESC'] = df['MIORRES'].apply(_standardize_finding_result)
    
    return df

def _transform_comments(df: pd.DataFrame) -> pd.DataFrame:
    """Transform comments data"""
    
    # Set default evaluator if not provided
    if 'COEVAL' not in df.columns:
        df['COEVAL'] = 'INVESTIGATOR'
    
    # Ensure COREF is populated
    if 'COREF' not in df.columns:
        df['COREF'] = 'GENERAL'
    
    # Clean up comment text
    if 'COCOMM' in df.columns:
        df['COCOMM'] = df['COCOMM'].astype(str).str.strip()
        df['COCOMM'] = df['COCOMM'].replace(['nan', 'None', 'NaN'], '')
    
    return df

def _transform_pharmacokinetic_concentrations(df: pd.DataFrame) -> pd.DataFrame:
    """Transform pharmacokinetic concentrations data"""
    
    # Set default specimen type if not provided
    if 'PCSPEC' not in df.columns:
        df['PCSPEC'] = 'PLASMA'
    
    # Standardize specimen terminology
    if 'PCSPEC' in df.columns:
        spec_mapping = {
            'BLOOD': 'BLOOD',
            'PLASMA': 'PLASMA', 
            'SERUM': 'SERUM',
            'URINE': 'URINE',
            'CSF': 'CSF',
            'TISSUE': 'TISSUE'
        }
        df['PCSPEC'] = df['PCSPEC'].astype(str).str.upper().map(spec_mapping).fillna(df['PCSPEC'])
    
    # Set default test codes for common analytes
    if 'PCTESTCD' not in df.columns and 'PCTEST' in df.columns:
        df['PCTESTCD'] = df['PCTEST'].apply(_generate_pc_test_code)
    
    # Ensure PCSTRESC is populated from PCORRES
    if 'PCSTRESC' not in df.columns and 'PCORRES' in df.columns:
        df['PCSTRESC'] = df['PCORRES'].astype(str).str.strip()
    
    # Convert numeric results to PCSTRESN
    if 'PCSTRESN' not in df.columns and 'PCORRES' in df.columns:
        df['PCSTRESN'] = df['PCORRES'].apply(_convert_to_numeric_result)
    
    # Standardize units
    if 'PCORRESU' in df.columns:
        unit_mapping = {
            'NG/ML': 'ng/mL',
            'UG/ML': 'μg/mL', 
            'MG/ML': 'mg/mL',
            'NMOL/L': 'nmol/L',
            'UMOL/L': 'μmol/L',
            'MMOL/L': 'mmol/L'
        }
        df['PCORRESU'] = df['PCORRESU'].astype(str).str.upper().map(unit_mapping).fillna(df['PCORRESU'])
    
    # Copy original units to standard units if not provided
    if 'PCSTRESU' not in df.columns and 'PCORRESU' in df.columns:
        df['PCSTRESU'] = df['PCORRESU']
    
    return df

def _transform_death_diagnosis(df: pd.DataFrame) -> pd.DataFrame:
    """Transform death diagnosis data"""
    
    # Set default test codes for death diagnosis
    if 'DDTESTCD' not in df.columns:
        df['DDTESTCD'] = 'NECROPSY'
    
    if 'DDTEST' not in df.columns:
        df['DDTEST'] = 'Cause of Death'
    
    # Standardize evaluator terminology
    if 'DDEVAL' not in df.columns:
        df['DDEVAL'] = 'PATHOLOGIST'
    
    if 'DDEVAL' in df.columns:
        eval_mapping = {
            'PATHOLOGIST': 'PATHOLOGIST',
            'VETERINARIAN': 'VETERINARIAN', 
            'INVESTIGATOR': 'INVESTIGATOR',
            'SPONSOR': 'SPONSOR',
            'CLINICIAN': 'VETERINARIAN'
        }
        df['DDEVAL'] = df['DDEVAL'].astype(str).str.upper().map(eval_mapping).fillna(df['DDEVAL'])
    
    # Standardize death diagnosis results
    if 'DDSTRESC' not in df.columns and 'DDORRES' in df.columns:
        df['DDSTRESC'] = df['DDORRES'].apply(_standardize_death_diagnosis)
    
    # Set default category
    if 'DDCAT' not in df.columns:
        df['DDCAT'] = 'PRIMARY'
    
    # Standardize category terminology
    if 'DDCAT' in df.columns:
        cat_mapping = {
            'PRIMARY': 'PRIMARY',
            'SECONDARY': 'SECONDARY',
            'CONTRIBUTING': 'CONTRIBUTING',
            'IMMEDIATE': 'IMMEDIATE',
            'UNDERLYING': 'UNDERLYING'
        }
        df['DDCAT'] = df['DDCAT'].astype(str).str.upper().map(cat_mapping).fillna(df['DDCAT'])
    
    return df

def _generate_pc_test_code(test_name: str) -> str:
    """Generate PC test code from test name"""
    if pd.isna(test_name) or test_name == '':
        return 'PARENT'
    
    # Common PC test code mappings
    test_codes = {
        'parent': 'PARENT',
        'parent compound': 'PARENT',
        'unchanged': 'PARENT',
        'metabolite': 'METAB1',
        'metabolite 1': 'METAB1',
        'metabolite 2': 'METAB2',
        'active metabolite': 'ACTMET',
        'total': 'TOTAL',
        'free': 'FREE',
        'bound': 'BOUND'
    }
    
    test_lower = str(test_name).lower().strip()
    
    for key, code in test_codes.items():
        if key in test_lower:
            return code
    
    # Generate code from test name
    if len(test_name) <= 8:
        return test_name.upper()
    else:
        # Take first 8 characters
        return test_name[:8].upper()

def _convert_to_numeric_result(result: str) -> float:
    """Convert PC result to numeric value"""
    if pd.isna(result) or result == '':
        return float('nan')
    
    result_str = str(result).strip()
    
    # Handle common non-numeric results
    if result_str.upper() in ['BLQ', 'BELOW LIMIT OF QUANTIFICATION', '<LOQ', 'ND', 'NOT DETECTED']:
        return float('nan')  # Or return 0 based on your requirements
    
    # Try to extract numeric value
    try:
        # Remove common non-numeric characters but keep decimal point
        cleaned = re.sub(r'[^\d\.\-\+eE]', '', result_str)
        if cleaned and cleaned not in ['.', '-', '+']:
            return float(cleaned)
    except (ValueError, AttributeError):
        pass
    
    return float('nan')

def _generate_test_code(test_name: str) -> str:
    """Generate test code from test name"""
    if pd.isna(test_name) or test_name == '':
        return ''
    
    # Common test code mappings
    test_codes = {
        'activity': 'CLACTIV',
        'salivation': 'CLSALIV',
        'respiration': 'CLRESP',
        'convulsion': 'CLCONV',
        'body weight': 'BW',
        'food consumption': 'FOODCON',
        'water consumption': 'WATERCON'
    }
    
    test_lower = str(test_name).lower().strip()
    
    for key, code in test_codes.items():
        if key in test_lower:
            return code
    
    # Generate code from first letters
    words = test_lower.split()[:2]  # Take first two words
    if words:
        code = ''.join(word[:2].upper() for word in words if word)
        return code[:8]  # Limit to 8 characters
    
    return 'UNKNOWN'

def _standardize_clinical_result(result: str) -> str:
    """Standardize clinical observation results"""
    if pd.isna(result) or result == '':
        return ''
    
    result_lower = str(result).lower().strip()
    
    # Map common results to standard terms
    if any(term in result_lower for term in ['normal', 'unremarkable', 'no findings']):
        return 'NORMAL'
    elif any(term in result_lower for term in ['abnormal', 'present', 'observed']):
        return 'ABNORMAL'
    else:
        return str(result).upper()

def _standardize_finding_result(result: str) -> str:
    """Standardize pathological finding results"""
    if pd.isna(result) or result == '':
        return 'NORMAL'
    
    result_lower = str(result).lower().strip()
    
    if any(term in result_lower for term in ['no visible lesions', 'normal', 'unremarkable']):
        return 'NORMAL'
    else:
        return 'ABNORMAL'

def _standardize_death_diagnosis(diagnosis: str) -> str:
    """Standardize death diagnosis terminology"""
    if pd.isna(diagnosis) or diagnosis == '':
        return ''
    
    diagnosis_lower = str(diagnosis).lower().strip()
    
    # Common death diagnosis mappings
    diagnosis_mappings = {
        # Scheduled termination
        'scheduled sacrifice': 'SCHEDULED SACRIFICE',
        'scheduled termination': 'SCHEDULED SACRIFICE',
        'terminal sacrifice': 'SCHEDULED SACRIFICE',
        'study termination': 'SCHEDULED SACRIFICE',
        'planned sacrifice': 'SCHEDULED SACRIFICE',
        
        # Natural death
        'found dead': 'FOUND DEAD',
        'natural death': 'FOUND DEAD',
        'spontaneous death': 'FOUND DEAD',
        
        # Moribund sacrifice
        'moribund sacrifice': 'MORIBUND SACRIFICE',
        'moribund': 'MORIBUND SACRIFICE',
        'euthanized moribund': 'MORIBUND SACRIFICE',
        'humane endpoint': 'MORIBUND SACRIFICE',
        
        # Accidental death
        'accidental death': 'ACCIDENTAL DEATH',
        'accident': 'ACCIDENTAL DEATH',
        'handling accident': 'ACCIDENTAL DEATH',
        'procedural accident': 'ACCIDENTAL DEATH',
        
        # Euthanasia
        'euthanized': 'EUTHANIZED',
        'euthanasia': 'EUTHANIZED',
        'humane euthanasia': 'EUTHANIZED',
        
        # Specific causes
        'organ failure': 'ORGAN FAILURE',
        'respiratory failure': 'RESPIRATORY FAILURE',
        'cardiac failure': 'CARDIAC FAILURE',
        'renal failure': 'RENAL FAILURE',
        'hepatic failure': 'HEPATIC FAILURE',
        'neurological': 'NEUROLOGICAL',
        'tumor': 'NEOPLASM',
        'neoplasm': 'NEOPLASM',
        'cancer': 'NEOPLASM'
    }
    
    # Check for exact matches first
    for key, standardized in diagnosis_mappings.items():
        if key in diagnosis_lower:
            return standardized
    
    # If no mapping found, return original diagnosis in uppercase
    return str(diagnosis).upper()


def _normalize_sequence_numbers(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Normalize sequence numbers to ensure uniqueness within subjects"""
    
    seq_col = f'{domain}SEQ'
    
    if seq_col in df.columns and 'USUBJID' in df.columns:
        # Sort by USUBJID to ensure consistent ordering
        df = df.sort_values(['USUBJID'])
        
        # Reset sequence numbers within each USUBJID
        df[seq_col] = df.groupby('USUBJID').cumcount() + 1
        
        logger.info(f"Normalized sequence numbers for {seq_col}")
    
    return df

def _apply_controlled_terminology(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Apply controlled terminology standardization"""
    
    # Common controlled terminology mappings
    ct_mappings = {
        'SEX': {'M': 'M', 'MALE': 'M', 'F': 'F', 'FEMALE': 'F'},
        'SPECIES': {'RAT': 'RAT', 'MOUSE': 'MOUSE', 'DOG': 'DOG', 'MONKEY': 'MONKEY'},
        'CLSEV': {
            'MINIMAL': 'MINIMAL', 'MIN': 'MINIMAL',
            'MILD': 'MILD', 'SLIGHT': 'MILD',
            'MODERATE': 'MODERATE', 'MOD': 'MODERATE',
            'MARKED': 'MARKED', 'SEVERE': 'SEVERE'
        },
        'EXROUTE': {
            'ORAL': 'ORAL', 'PO': 'ORAL',
            'IV': 'IV', 'INTRAVENOUS': 'IV',
            'SC': 'SC', 'SUBCUTANEOUS': 'SC',
            'IM': 'IM', 'INTRAMUSCULAR': 'IM'
        },
        'LBBLFL': {'Y': 'Y', 'YES': 'Y', 'N': 'N', 'NO': 'N'}
    }
    
    for col, mapping in ct_mappings.items():
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().map(mapping).fillna(df[col])
    
    return df

def _final_cleanup(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Final cleanup and validation"""
    
    # Remove any completely empty rows
    df = df.dropna(how='all')
    
    # Remove duplicate rows based on key variables
    key_cols = ['STUDYID', 'USUBJID']
    seq_col = f'{domain}SEQ'
    if seq_col in df.columns:
        key_cols.append(seq_col)
    
    # Keep only columns that exist
    existing_key_cols = [col for col in key_cols if col in df.columns]
    if existing_key_cols:
        df = df.drop_duplicates(subset=existing_key_cols, keep='first')
    
    # Reset index
    df = df.reset_index(drop=True)
    
    # Ensure all string columns are properly cleaned
    string_cols = df.select_dtypes(include=['object']).columns
    for col in string_cols:
        df[col] = df[col].astype(str).replace('nan', '').replace('None', '')
    
    return df

def _sort_domain_data(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Sort data according to SEND conventions"""
    
    # Define sort order
    sort_cols = []
    
    # Primary sort by USUBJID if available
    if 'USUBJID' in df.columns:
        sort_cols.append('USUBJID')
    
    # Secondary sort by sequence number if available
    seq_col = f'{domain}SEQ'
    if seq_col in df.columns:
        sort_cols.append(seq_col)
    
    # Tertiary sort by visit day if available
    if 'VISITDY' in df.columns:
        sort_cols.append('VISITDY')
    elif f'{domain}DY' in df.columns:
        sort_cols.append(f'{domain}DY')
    
    # Sort if we have sorting columns
    if sort_cols:
        existing_sort_cols = [col for col in sort_cols if col in df.columns]
        if existing_sort_cols:
            df = df.sort_values(existing_sort_cols)
            df = df.reset_index(drop=True)
    
    return df

# Additional utility functions for data validation
def validate_domain_data(df: pd.DataFrame, domain: str) -> Dict[str, Any]:
    """Validate domain data and return validation results"""
    
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'info': {
            'record_count': len(df),
            'column_count': len(df.columns) if not df.empty else 0,
            'completeness': 0.0
        }
    }
    
    if df.empty:
        results['errors'].append("Empty dataset")
        results['valid'] = False
        return results
    
    # Check required columns
    required_cols = ['STUDYID', 'DOMAIN', 'USUBJID']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        results['errors'].extend([f"Missing required column: {col}" for col in missing_cols])
        results['valid'] = False
    
    # Check data completeness
    total_cells = df.size
    empty_cells = df.isna().sum().sum() + (df == '').sum().sum()
    completeness = ((total_cells - empty_cells) / total_cells * 100) if total_cells > 0 else 0
    results['info']['completeness'] = round(completeness, 2)
    
    if completeness < 90:
        results['warnings'].append(f"Low data completeness: {completeness:.1f}%")
    
    return results

def validate_column_mapping(df: pd.DataFrame, domain: str, column_mapping: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Validate column mapping and provide suggestions for unmapped columns
    
    Args:
        df (pd.DataFrame): Input dataframe
        domain (str): SEND domain code
        column_mapping (Dict[str, str], optional): Current column mapping
        
    Returns:
        Dict[str, Any]: Validation results with suggestions
    """
    
    required_cols = get_required_columns(domain)
    current_cols = list(df.columns)
    
    results = {
        'mapped_columns': [],
        'unmapped_columns': [],
        'missing_required': [],
        'suggestions': []
    }
    
    # Check which required columns are mapped
    for req_col in required_cols:
        if req_col in current_cols:
            description = get_column_description(domain, req_col)
            results['mapped_columns'].append({
                'column': req_col,
                'description': description
            })
        else:
            description = get_column_description(domain, req_col)
            results['missing_required'].append({
                'column': req_col,
                'description': description
            })
    
    # Identify unmapped columns
    mapped_cols = [col for col in current_cols if col in required_cols]
    results['unmapped_columns'] = [col for col in current_cols if col not in mapped_cols]
    
    # Provide suggestions for unmapped columns
    for unmapped_col in results['unmapped_columns']:
        suggestions = _suggest_column_mapping(unmapped_col, required_cols, domain)
        if suggestions:
            results['suggestions'].append({
                'source_column': unmapped_col,
                'suggested_mappings': suggestions
            })
    
    return results

def _suggest_column_mapping(source_col: str, target_cols: List[str], domain: str) -> List[Dict[str, str]]:
    """Suggest possible column mappings based on column names and descriptions"""
    import difflib
    
    suggestions = []
    source_lower = source_col.lower()
    
    # Use fuzzy matching to find similar column names
    matches = difflib.get_close_matches(source_lower, [col.lower() for col in target_cols], n=3, cutoff=0.6)
    
    for match in matches:
        # Find the original case column name
        target_col = next(col for col in target_cols if col.lower() == match)
        description = get_column_description(domain, target_col)
        suggestions.append({
            'target_column': target_col,
            'description': description,
            'similarity': difflib.SequenceMatcher(None, source_lower, match).ratio()
        })
    
    return suggestions