#!/usr/bin/env python3
"""
Convert SENDIG TE Domain CSV data to XPT format for FDA submission
Study: 1121-2781 - A 7-Day Repeat Dose Toxicity Study of BLU-525

Requirements:
pip install pandas pyreadstat
"""

import pandas as pd
import pyreadstat
from datetime import datetime
import os

def prepare_dataframe_for_sas(df, domain_code):
    """Prepare DataFrame for SAS XPT format - based on pipeline approach"""
    df_prepared = df.copy()
    
    # Ensure DOMAIN column exists and is set correctly
    df_prepared['DOMAIN'] = domain_code.upper()
    
    # SAS XPT format constraints
    MAX_STRING_LENGTH = 200
    
    # Fix data types and values
    for col in df_prepared.columns:
        if col in ['TESEQ', 'VISITNUM', 'VISITDY']:
            # Numeric columns - convert to float64 (SAS numeric type)
            df_prepared[col] = pd.to_numeric(df_prepared[col], errors='coerce')
            df_prepared[col] = df_prepared[col].fillna(0).astype('float64')
        else:
            # String columns
            df_prepared[col] = df_prepared[col].astype(str)
            df_prepared[col] = df_prepared[col].replace(['nan', 'None', 'NaN'], '')
            df_prepared[col] = df_prepared[col].str[:MAX_STRING_LENGTH]
            # Remove any problematic characters
            df_prepared[col] = df_prepared[col].str.replace(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', regex=True)
    
    print(f"Data preparation complete:")
    print(f"- Shape: {df_prepared.shape}")
    print(f"- Data types: {df_prepared.dtypes.to_dict()}")
    print(f"- Sample record:\n{df_prepared.iloc[0].to_dict()}")
    
    return df_prepared

def create_te_xpt_file():
    """
    Create XPT file from TE domain CSV data according to SENDIG standards
    """
    
    # TE domain CSV data (can be read from file or defined here)
    te_csv_data = """STUDYID,DOMAIN,USUBJID,TESEQ,TESPEC,TELOC,TEORRES,TESTRESC,TESEV,VISITNUM,VISITDY,TESPID
1121-2781,TE,1001,1,HEART,RIGHT VENTRICLE EPICARDIUM,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 2,1,8,TE000001
1121-2781,TE,1001,2,LIVER,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000002
1121-2781,TE,1002,3,KIDNEYS,,CAST HYALINE,CAST HYALINE,GRADE 1,1,8,TE000003
1121-2781,TE,1002,4,HEART,LEFT VENTRICLE,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 1,1,8,TE000004
1121-2781,TE,1002,5,LIVER,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000005
1121-2781,TE,1003,6,KIDNEYS,,NEPHROPATHY CHRONIC PROGRESSIVE,NEPHROPATHY CHRONIC PROGRESSIVE,GRADE 1,1,8,TE000006
1121-2781,TE,1003,7,TESTES,TUBULE UNILATERAL,DEGENERATION,DEGENERATION,GRADE 1,1,8,TE000007
1121-2781,TE,1003,8,EPIDIDYMIDES,LUMEN UNILATERAL,CELL DEBRIS,CELL DEBRIS,GRADE 2,1,8,TE000008
1121-2781,TE,1004,9,MULTIPLE ORGANS,,NO ABNORMALITIES DETECTED,NO ABNORMALITIES DETECTED,,1,8,TE000009
1121-2781,TE,1005,10,KIDNEYS,,BASOPHILIA TUBULE,BASOPHILIA TUBULE,GRADE 1,1,8,TE000010
1121-2781,TE,1005,11,HEART,RIGHT VENTRICLE,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 2,1,8,TE000011
1121-2781,TE,2001,12,KIDNEYS,,BASOPHILIA TUBULE,BASOPHILIA TUBULE,GRADE 1,1,8,TE000012
1121-2781,TE,2001,13,KIDNEYS,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000013
1121-2781,TE,2001,14,TESTES,TUBULE UNILATERAL,DEGENERATION,DEGENERATION,GRADE 1,1,8,TE000014
1121-2781,TE,2001,15,HEART,RIGHT VENTRICLE EPICARDIUM,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 1,1,8,TE000015
1121-2781,TE,2001,16,SPLEEN,,EXTRAMEDULLARY HEMATOPOIESIS INCREASED,EXTRAMEDULLARY HEMATOPOIESIS INCREASED,GRADE 1,1,8,TE000016
1121-2781,TE,2001,17,EPIDIDYMIDES,LUMEN UNILATERAL,CELL DEBRIS,CELL DEBRIS,GRADE 1,1,8,TE000017
1121-2781,TE,2002,18,HEART,RIGHT VENTRICLE,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 1,1,8,TE000018
1121-2781,TE,2002,19,LIVER,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000019
1121-2781,TE,2003,20,TESTES,TUBULE UNILATERAL,DEGENERATION,DEGENERATION,GRADE 1,1,8,TE000020
1121-2781,TE,2003,21,EPIDIDYMIDES,LUMEN UNILATERAL,CELL DEBRIS,CELL DEBRIS,GRADE 1,1,8,TE000021
1121-2781,TE,2003,22,EPIDIDYMIDES,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000022
1121-2781,TE,2004,23,HEART,RIGHT VENTRICLE,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 1,1,8,TE000023
1121-2781,TE,2004,24,LIVER,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000024
1121-2781,TE,2005,25,LIVER,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000025
1121-2781,TE,3001,26,KIDNEYS,,BASOPHILIA TUBULE,BASOPHILIA TUBULE,GRADE 1,1,8,TE000026
1121-2781,TE,3001,27,HEART,RIGHT VENTRICLE,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 1,1,8,TE000027
1121-2781,TE,3001,28,SPLEEN,,EXTRAMEDULLARY HEMATOPOIESIS INCREASED,EXTRAMEDULLARY HEMATOPOIESIS INCREASED,GRADE 1,1,8,TE000028
1121-2781,TE,3001,29,EPIDIDYMIDES,LUMEN UNILATERAL,CELL DEBRIS,CELL DEBRIS,GRADE 1,1,8,TE000029
1121-2781,TE,3001,30,EPIDIDYMIDES,UNILATERAL,HYPOSPERMIA,HYPOSPERMIA,GRADE 5,1,8,TE000030
1121-2781,TE,3002,31,HEART,RIGHT VENTRICLE,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 2,1,8,TE000031
1121-2781,TE,3002,32,LIVER,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000032
1121-2781,TE,3003,33,MULTIPLE ORGANS,,NO ABNORMALITIES DETECTED,NO ABNORMALITIES DETECTED,,1,8,TE000033
1121-2781,TE,3004,34,HEART,RIGHT VENTRICLE,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 2,1,8,TE000034
1121-2781,TE,3004,35,LIVER,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000035
1121-2781,TE,3004,36,LUNG,,AGGREGATES ALVEOLAR MACROPHAGE,AGGREGATES ALVEOLAR MACROPHAGE,GRADE 1,1,8,TE000036
1121-2781,TE,3004,37,STOMACH,GLAND FOCAL,DILATION,DILATION,GRADE 1,1,8,TE000037
1121-2781,TE,3005,38,KIDNEYS,,NEPHROPATHY CHRONIC PROGRESSIVE,NEPHROPATHY CHRONIC PROGRESSIVE,GRADE 1,1,8,TE000038
1121-2781,TE,3005,39,HEART,RIGHT VENTRICLE,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 1,1,8,TE000039
1121-2781,TE,3005,40,LIVER,,EXTRAMEDULLARY HEMATOPOIESIS,EXTRAMEDULLARY HEMATOPOIESIS,GRADE 1,1,8,TE000040
1121-2781,TE,4001,41,KIDNEYS,,BASOPHILIA TUBULE,BASOPHILIA TUBULE,GRADE 1,1,8,TE000041
1121-2781,TE,4001,42,TESTES,TUBULE BILATERAL,DEGENERATION,DEGENERATION,GRADE 1,1,8,TE000042
1121-2781,TE,4001,43,HEART,RIGHT VENTRICLE,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 1,1,8,TE000043
1121-2781,TE,4001,44,EPIDIDYMIDES,LUMEN BILATERAL,CELL DEBRIS,CELL DEBRIS,GRADE 1,1,8,TE000044
1121-2781,TE,4002,45,HEART,LEFT VENTRICLE,NECROSIS/INFLAMMATORY CELL INFILTRATE,NECROSIS/INFLAMMATORY CELL INFILTRATE,GRADE 1,1,8,TE000045
1121-2781,TE,4003,46,KIDNEYS,,CAST HYALINE,CAST HYALINE,GRADE 1,1,8,TE000046
1121-2781,TE,4004,47,LIVER,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000047
1121-2781,TE,4005,48,KIDNEYS,,CAST HYALINE,CAST HYALINE,GRADE 1,1,8,TE000048
1121-2781,TE,4005,49,LIVER,,INFILTRATE MONONUCLEAR CELL,INFILTRATE MONONUCLEAR CELL,GRADE 1,1,8,TE000049"""
    
    # Read CSV data into DataFrame
    from io import StringIO
    df = pd.read_csv(StringIO(te_csv_data))
    
    # Fix USUBJID to follow CDISC standard: STUDYID-SUBJID
    print("Fixing USUBJID format to STUDYID-SUBJID...")
    df['USUBJID'] = df['STUDYID'] + '-' + df['USUBJID'].astype(str)
    print(f"Sample USUBJID values: {df['USUBJID'].head(3).tolist()}")
    
    # Data type specifications for SENDIG TE domain
    dtype_dict = {
        'STUDYID': str,
        'DOMAIN': str, 
        'USUBJID': str,
        'TESEQ': int,
        'TESPEC': str,
        'TELOC': str,
        'TEORRES': str,
        'TESTRESC': str,
        'TESEV': str,
        'VISITNUM': int,
        'VISITDY': int,
        'TESPID': str
    }
    
    # Apply data types
    for col, dtype in dtype_dict.items():
        if col in df.columns:
            if dtype == str:
                df[col] = df[col].astype(str)
                # Replace 'nan' with empty string for character variables
                df[col] = df[col].replace('nan', '')
            else:
                df[col] = df[col].astype(dtype)
    
    # Set variable lengths according to SENDIG standards
    var_lengths = {
        'STUDYID': 20,
        'DOMAIN': 2,
        'USUBJID': 15,
        'TESPEC': 40,
        'TELOC': 40,
        'TEORRES': 200,
        'TESTRESC': 200,
        'TESEV': 20,
        'TESPID': 20
    }
    
    # Truncate strings to specified lengths
    for col, length in var_lengths.items():
        if col in df.columns:
            df[col] = df[col].str[:length]
    
    # Create dataset metadata
    dataset_metadata = {
        'name': 'TE',
        'label': 'Tissue Examination',
        'created': datetime.now(),
        'modified': datetime.now()
    }
    
    # Create variable metadata dictionary
    var_metadata = {
        'STUDYID': {'label': 'Study Identifier', 'type': 'char', 'length': 20},
        'DOMAIN': {'label': 'Domain Abbreviation', 'type': 'char', 'length': 2},
        'USUBJID': {'label': 'Unique Subject Identifier', 'type': 'char', 'length': 15},
        'TESEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
        'TESPEC': {'label': 'Specimen Type', 'type': 'char', 'length': 40},
        'TELOC': {'label': 'Location of Finding', 'type': 'char', 'length': 40},
        'TEORRES': {'label': 'Result as Originally Received', 'type': 'char', 'length': 200},
        'TESTRESC': {'label': 'Character Result/Finding', 'type': 'char', 'length': 200},
        'TESEV': {'label': 'Severity/Grade', 'type': 'char', 'length': 20},
        'VISITNUM': {'label': 'Visit Number', 'type': 'num', 'length': 8},
        'VISITDY': {'label': 'Planned Study Day of Visit', 'type': 'num', 'length': 8},
        'TESPID': {'label': 'Sponsor-Defined Identifier', 'type': 'char', 'length': 20}
    }
    
    # Save as CSV first (backup)
    csv_filename = 'te_domain_1121-2781.csv'
    df.to_csv(csv_filename, index=False)
    print(f"CSV file saved: {csv_filename}")
    
    # Create XPT file using pyreadstat
    xpt_filename = 'TE.xpt'
    
    # Prepare variable labels for pyreadstat
    variable_labels = {col: var_metadata[col]['label'] for col in df.columns if col in var_metadata}
    
    # Write to XPT format using pyreadstat (corrected parameters)
    pyreadstat.write_xport(df, xpt_filename, 
                          table_name='TE',
                          file_format_version=5)
    
    print(f"XPT file created: {xpt_filename}")
    print(f"Dataset contains {len(df)} records")
    print(f"Variables: {list(df.columns)}")
    
    # Debug: Check if XPT file was created and has content
    if os.path.exists(xpt_filename):
        file_size = os.path.getsize(xpt_filename)
        print(f"XPT file size: {file_size} bytes")
        
        # Try to read back the XPT file to verify
        try:
            df_read, meta = pyreadstat.read_xport(xpt_filename)
            print(f"Verification: Read back {len(df_read)} records from XPT file")
            print(f"Columns in XPT: {list(df_read.columns)}")
            if len(df_read) > 0:
                print("Sample data from XPT:")
                print(df_read.head(3))
            else:
                print("WARNING: XPT file contains no data!")
        except Exception as e:
            print(f"Error reading back XPT file: {e}")
    else:
        print("ERROR: XPT file was not created!")
    
    # Display summary statistics
    print("\nDataset Summary:")
    print(f"- Total records: {len(df)}")
    print(f"- Unique subjects: {df['USUBJID'].nunique()}")
    print(f"- Unique specimens: {df['TESPEC'].nunique()}")
    print(f"- Records with findings: {len(df[df['TEORRES'] != 'NO ABNORMALITIES DETECTED'])}")
    print(f"- Records with no abnormalities: {len(df[df['TEORRES'] == 'NO ABNORMALITIES DETECTED'])}")
    
    print("\nFinding distribution by specimen:")
    print(df['TESPEC'].value_counts())
    
    print("\nSeverity distribution:")
    print(df['TESEV'].value_counts())
    
    return df

def validate_te_domain(df):
    """
    Validate TE domain data according to SENDIG rules
    """
    print("\n=== TE Domain Validation ===")
    
    validation_errors = []
    
    # Required variables check
    required_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'TESEQ']
    for var in required_vars:
        if var not in df.columns:
            validation_errors.append(f"Missing required variable: {var}")
        elif df[var].isnull().any():
            validation_errors.append(f"Null values found in required variable: {var}")
    
    # Domain value check
    if 'DOMAIN' in df.columns:
        if not all(df['DOMAIN'] == 'TE'):
            validation_errors.append("DOMAIN should be 'TE' for all records")
    
    # TESEQ uniqueness check
    if 'TESEQ' in df.columns:
        if df['TESEQ'].duplicated().any():
            validation_errors.append("TESEQ values should be unique")
    
    # Check for proper sequence numbering
    if 'TESEQ' in df.columns:
        expected_seq = list(range(1, len(df) + 1))
        actual_seq = sorted(df['TESEQ'].tolist())
        if actual_seq != expected_seq:
            validation_errors.append("TESEQ should be consecutive integers starting from 1")
    
    if validation_errors:
        print("Validation FAILED:")
        for error in validation_errors:
            print(f"  - {error}")
    else:
        print("Validation PASSED: All checks successful")
    
    return len(validation_errors) == 0

if __name__ == "__main__":
    print("Creating SENDIG TE Domain XPT file...")
    print("=" * 50)
    
    # Create the XPT file
    te_df = create_te_xpt_file()
    
    # Validate the data
    is_valid = validate_te_domain(te_df)
    
    print("\n" + "=" * 50)
    if is_valid:
        print("SUCCESS: TE domain XPT file created and validated")
        print("Files ready for FDA submission:")
        print("  - te.xpt (SAS Transport file)")
        print("  - te_domain_1121-2781.csv (backup CSV)")
    else:
        print("WARNING: Validation issues found. Please review before submission.")