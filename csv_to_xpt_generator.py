#!/usr/bin/env python3
"""
SEND CSV to XPT Converter with Proper Metadata
Converts SEND domain CSV files to SAS XPT format for FDA submission
Uses pyreadstat for better XPT compatibility and metadata handling

Requirements:
pip install pandas pyreadstat

Usage:
python csv_to_xpt_converter.py
"""

import pandas as pd
import pyreadstat
import os
import sys
from pathlib import Path
from datetime import datetime
import logging
from io import StringIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('conversion.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class SENDConverter:
    """Converts SEND CSV files to XPT format with proper metadata for XPT viewers"""
    
    def __init__(self):
        # Define all SEND domains with proper metadata
        self.send_domains = {
            'TS': {'name': 'Trial Summary', 'description': 'Trial Summary'},
            'TA': {'name': 'Trial Arms', 'description': 'Trial Arms'}, 
            'TE': {'name': 'Trial Elements', 'description': 'Trial Elements'},
            'TX': {'name': 'Trial Sets', 'description': 'Trial Sets'},
            'DM': {'name': 'Demographics', 'description': 'Demographics'},
            'SE': {'name': 'Subject Elements', 'description': 'Subject Elements'},
            'DS': {'name': 'Disposition', 'description': 'Disposition'},
            'EX': {'name': 'Exposure', 'description': 'Exposure'},
            'PC': {'name': 'Pharmacokinetics Concentrations', 'description': 'Pharmacokinetics Concentrations'},
            'PP': {'name': 'Pharmacokinetics Parameters', 'description': 'Pharmacokinetics Parameters'},
            'LB': {'name': 'Laboratory Test Results', 'description': 'Laboratory Test Results'},
            'CL': {'name': 'Clinical Observations', 'description': 'Clinical Observations'},
            'FW': {'name': 'Food and Water Consumption', 'description': 'Food and Water Consumption'},
            'BW': {'name': 'Body Weights', 'description': 'Body Weights'},
            'OM': {'name': 'Organ Measurements', 'description': 'Organ Measurements'},
            'MA': {'name': 'Macroscopic Findings', 'description': 'Macroscopic Findings'},
            'MI': {'name': 'Microscopic Findings', 'description': 'Microscopic Findings'},
            'CO': {'name': 'Comments', 'description': 'Comments'}
        }
        
        # XPT file constraints
        self.max_variable_name_length = 8
        self.max_label_length = 40
        self.max_string_length = 200
        
    def get_variable_metadata(self, domain, columns):
        """Get variable metadata for each SEND domain"""
        
        # Common variables across domains
        common_metadata = {
            'STUDYID': {'label': 'Study Identifier', 'type': 'char', 'length': 20},
            'DOMAIN': {'label': 'Domain Abbreviation', 'type': 'char', 'length': 2},
            'USUBJID': {'label': 'Unique Subject Identifier', 'type': 'char', 'length': 64},
        }
        
        # Domain-specific metadata
        domain_metadata = {
            'TS': {
                'TSSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'TSPARMCD': {'label': 'Trial Summary Parameter Short Name', 'type': 'char', 'length': 8},
                'TSPARM': {'label': 'Trial Summary Parameter', 'type': 'char', 'length': 40},
                'TSVAL': {'label': 'Parameter Value', 'type': 'char', 'length': 200},
                'TSVALNF': {'label': 'Parameter Null Flavor', 'type': 'char', 'length': 8}
            },
            'TA': {
                'ARMCD': {'label': 'Planned Arm Code', 'type': 'char', 'length': 20},
                'ARM': {'label': 'Description of Planned Arm', 'type': 'char', 'length': 200},
                'ARMTYPE': {'label': 'Arm Type', 'type': 'char', 'length': 20},
                'ARMSEQ': {'label': 'Arm Sequence Number', 'type': 'num', 'length': 8},
                'ARMDESC': {'label': 'Arm Description', 'type': 'char', 'length': 200},
                'TAETORD': {'label': 'Planned Order of Element within Arm', 'type': 'num', 'length': 8},
                'EPOCH': {'label': 'Epoch', 'type': 'char', 'length': 20},
                'ELEMENT': {'label': 'Element Name', 'type': 'char', 'length': 8}
            },
            'TE': {
                'TESEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'TESTRL': {'label': 'Element Start Rule', 'type': 'char', 'length': 10},
                'TEENRL': {'label': 'Element End Rule', 'type': 'char', 'length': 10},
                'TEDUR': {'label': 'Planned Duration of Element', 'type': 'char', 'length': 8},
                'TEPROT': {'label': 'Protocol', 'type': 'char', 'length': 200}
            },
            'TX': {
                'SETCD': {'label': 'Set Code', 'type': 'char', 'length': 8},
                'SET': {'label': 'Set Description', 'type': 'char', 'length': 40},
                'SETTYPE': {'label': 'Set Type', 'type': 'char', 'length': 20},
                'SETDESC': {'label': 'Set Description Text', 'type': 'char', 'length': 200},
                'TXSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'SETPNCD': {'label': 'Set Planned Code', 'type': 'char', 'length': 8},
                'SETPLAN': {'label': 'Planned Set Flag', 'type': 'char', 'length': 1}
            },
            'DM': {
                'DMSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'SUBJID': {'label': 'Subject Identifier for the Study', 'type': 'char', 'length': 64},
                'RFSTDTC': {'label': 'Subject Reference Start Date/Time', 'type': 'char', 'length': 19},
                'RFENDTC': {'label': 'Subject Reference End Date/Time', 'type': 'char', 'length': 19},
                'RFXSTDTC': {'label': 'Date/Time of First Study Treatment', 'type': 'char', 'length': 19},
                'RFXENDTC': {'label': 'Date/Time of Last Study Treatment', 'type': 'char', 'length': 19},
                'SITEID': {'label': 'Study Site Identifier', 'type': 'char', 'length': 15},
                'BRTHDTC': {'label': 'Date/Time of Birth', 'type': 'char', 'length': 19},
                'AGE': {'label': 'Age', 'type': 'num', 'length': 8},
                'AGEU': {'label': 'Age Units', 'type': 'char', 'length': 40},
                'SEX': {'label': 'Sex', 'type': 'char', 'length': 1},
                'RACE': {'label': 'Race', 'type': 'char', 'length': 40},
                'SPECIES': {'label': 'Species', 'type': 'char', 'length': 40},
                'STRAIN': {'label': 'Strain', 'type': 'char', 'length': 40},
                'SBSTRAIN': {'label': 'Substrain', 'type': 'char', 'length': 40},
                'ARMCD': {'label': 'Planned Arm Code', 'type': 'char', 'length': 20},
                'ARM': {'label': 'Description of Planned Arm', 'type': 'char', 'length': 200},
                'SETCD': {'label': 'Set Code', 'type': 'char', 'length': 8}
            },
            'SE': {
                'SESEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'ETCD': {'label': 'Element Code', 'type': 'char', 'length': 8},
                'ELEMENT': {'label': 'Element Name', 'type': 'char', 'length': 8},
                'SESTDTC': {'label': 'Start Date/Time of Element', 'type': 'char', 'length': 19},
                'SEENDTC': {'label': 'End Date/Time of Element', 'type': 'char', 'length': 19},
                'SEUPDES': {'label': 'Description of Unplanned Element', 'type': 'char', 'length': 200}
            },
            'DS': {
                'DSSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'DSTERM': {'label': 'Reported Term for the Disposition Event', 'type': 'char', 'length': 200},
                'DSDECOD': {'label': 'Standardized Disposition Term', 'type': 'char', 'length': 200},
                'DSCAT': {'label': 'Category for Disposition Event', 'type': 'char', 'length': 40},
                'DSSTDTC': {'label': 'Start Date/Time of Disposition Event', 'type': 'char', 'length': 19},
                'DSDY': {'label': 'Study Day of Disposition Event', 'type': 'num', 'length': 8}
            },
            'EX': {
                'EXSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'EXTRT': {'label': 'Name of Treatment', 'type': 'char', 'length': 200},
                'EXDOSE': {'label': 'Dose', 'type': 'num', 'length': 8},
                'EXDOSU': {'label': 'Dose Units', 'type': 'char', 'length': 40},
                'EXDOSFRM': {'label': 'Dose Form', 'type': 'char', 'length': 40},
                'EXDOSFRQ': {'label': 'Dosing Frequency per Interval', 'type': 'char', 'length': 40},
                'EXROUTE': {'label': 'Route of Administration', 'type': 'char', 'length': 40},
                'EXLOT': {'label': 'Lot Number', 'type': 'char', 'length': 40},
                'EXMFDT': {'label': 'Manufacture Date', 'type': 'char', 'length': 19},
                'EXEXPDT': {'label': 'Expiration Date', 'type': 'char', 'length': 19},
                'EXSTDTC': {'label': 'Start Date/Time of Treatment', 'type': 'char', 'length': 19},
                'EXENDTC': {'label': 'End Date/Time of Treatment', 'type': 'char', 'length': 19},
                'EXSTDY': {'label': 'Study Day of Start of Treatment', 'type': 'num', 'length': 8},
                'EXENDY': {'label': 'Study Day of End of Treatment', 'type': 'num', 'length': 8},
                'EXDOSRGM': {'label': 'Intended Dose Regimen', 'type': 'char', 'length': 40}
            },
            'PC': {
                'PCSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'PCTESTCD': {'label': 'PC Test Short Name', 'type': 'char', 'length': 8},
                'PCTEST': {'label': 'PC Test Name', 'type': 'char', 'length': 40},
                'PCCAT': {'label': 'Category for PC', 'type': 'char', 'length': 40},
                'PCSCAT': {'label': 'Subcategory for PC', 'type': 'char', 'length': 40},
                'PCORRES': {'label': 'Result as Originally Received', 'type': 'char', 'length': 200},
                'PCORRESU': {'label': 'Original Units', 'type': 'char', 'length': 40},
                'PCSTRESC': {'label': 'Character Result/Finding', 'type': 'char', 'length': 200},
                'PCSTRESN': {'label': 'Numeric Result/Finding', 'type': 'num', 'length': 8},
                'PCSTRESU': {'label': 'Standard Units', 'type': 'char', 'length': 40},
                'PCSTAT': {'label': 'Completion Status', 'type': 'char', 'length': 40},
                'PCREASND': {'label': 'Reason Not Done', 'type': 'char', 'length': 200},
                'PCDTC': {'label': 'Date/Time of Collection', 'type': 'char', 'length': 19},
                'PCDY': {'label': 'Study Day of Collection', 'type': 'num', 'length': 8},
                'PCTPT': {'label': 'Planned Time Point Name', 'type': 'char', 'length': 40},
                'PCTPTNUM': {'label': 'Planned Time Point Number', 'type': 'num', 'length': 8},
                'PCELTM': {'label': 'Planned Elapsed Time from Time Point Ref', 'type': 'char', 'length': 20},
                'PCFAST': {'label': 'Fasting Status', 'type': 'char', 'length': 1},
                'PCLLOQ': {'label': 'Lower Limit of Quantitation', 'type': 'num', 'length': 8},
                'PCMETHOD': {'label': 'Method of Test or Examination', 'type': 'char', 'length': 40},
                'PCSPEC': {'label': 'Specimen Type', 'type': 'char', 'length': 40}
            },
            'PP': {
                'PPSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'PPGRPID': {'label': 'Group ID', 'type': 'char', 'length': 40},
                'PPTESTCD': {'label': 'PP Test Short Name', 'type': 'char', 'length': 8},
                'PPTEST': {'label': 'PP Test Name', 'type': 'char', 'length': 40},
                'PPCAT': {'label': 'Category for PP', 'type': 'char', 'length': 40},
                'PPSCAT': {'label': 'Subcategory for PP', 'type': 'char', 'length': 40},
                'PPORRES': {'label': 'Result as Originally Received', 'type': 'char', 'length': 200},
                'PPORRESU': {'label': 'Original Units', 'type': 'char', 'length': 40},
                'PPSTRESC': {'label': 'Character Result/Finding', 'type': 'char', 'length': 200},
                'PPSTRESN': {'label': 'Numeric Result/Finding', 'type': 'num', 'length': 8},
                'PPSTRESU': {'label': 'Standard Units', 'type': 'char', 'length': 40},
                'PPSTAT': {'label': 'Completion Status', 'type': 'char', 'length': 40},
                'PPREASND': {'label': 'Reason Not Done', 'type': 'char', 'length': 200},
                'PPSPEC': {'label': 'Specimen Type', 'type': 'char', 'length': 40},
                'PPMETHOD': {'label': 'Method of Test or Examination', 'type': 'char', 'length': 40},
                'PPDTC': {'label': 'Date/Time of Collection', 'type': 'char', 'length': 19},
                'PPDY': {'label': 'Study Day of Collection', 'type': 'num', 'length': 8}
            },
            'LB': {
                'LBSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'LBGRPID': {'label': 'Group ID', 'type': 'char', 'length': 40},
                'LBTESTCD': {'label': 'Lab Test Short Name', 'type': 'char', 'length': 8},
                'LBTEST': {'label': 'Lab Test Name', 'type': 'char', 'length': 40},
                'LBCAT': {'label': 'Category for Lab Test', 'type': 'char', 'length': 40},
                'LBSCAT': {'label': 'Subcategory for Lab Test', 'type': 'char', 'length': 40},
                'LBORRES': {'label': 'Result as Originally Received', 'type': 'char', 'length': 200},
                'LBORRESU': {'label': 'Original Units', 'type': 'char', 'length': 40},
                'LBORNRLO': {'label': 'Reference Range Lower Limit', 'type': 'char', 'length': 40},
                'LBORNRHI': {'label': 'Reference Range Upper Limit', 'type': 'char', 'length': 40},
                'LBSTRESC': {'label': 'Character Result/Finding', 'type': 'char', 'length': 200},
                'LBSTRESN': {'label': 'Numeric Result/Finding', 'type': 'num', 'length': 8},
                'LBSTRESU': {'label': 'Standard Units', 'type': 'char', 'length': 40},
                'LBNRIND': {'label': 'Reference Range Indicator', 'type': 'char', 'length': 40},
                'LBSTAT': {'label': 'Completion Status', 'type': 'char', 'length': 40},
                'LBREASND': {'label': 'Reason Not Done', 'type': 'char', 'length': 200},
                'LBBLFL': {'label': 'Baseline Flag', 'type': 'char', 'length': 1},
                'LBDTC': {'label': 'Date/Time of Collection', 'type': 'char', 'length': 19},
                'LBDY': {'label': 'Study Day of Collection', 'type': 'num', 'length': 8},
                'LBTPT': {'label': 'Planned Time Point Name', 'type': 'char', 'length': 40},
                'LBTPTREF': {'label': 'Time Point Reference', 'type': 'char', 'length': 40},
                'LBTPTNUM': {'label': 'Planned Time Point Number', 'type': 'num', 'length': 8},
                'LBELTM': {'label': 'Planned Elapsed Time from Time Point Ref', 'type': 'char', 'length': 20},
                'LBFASTYN': {'label': 'Fasting Status', 'type': 'char', 'length': 1},
                'LBREFID': {'label': 'Reference ID', 'type': 'char', 'length': 40},
                'LBLLOQ': {'label': 'Lower Limit of Quantitation', 'type': 'num', 'length': 8},
                'LBULOQ': {'label': 'Upper Limit of Quantitation', 'type': 'num', 'length': 8}
            },
            'CL': {
                'CLSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'CLGRPID': {'label': 'Group ID', 'type': 'char', 'length': 40},
                'CLTESTCD': {'label': 'Clinical Observation Test Short Name', 'type': 'char', 'length': 8},
                'CLTEST': {'label': 'Clinical Observation Test Name', 'type': 'char', 'length': 40},
                'CLCAT': {'label': 'Category for Clinical Observation', 'type': 'char', 'length': 40},
                'CLSCAT': {'label': 'Subcategory for Clinical Observation', 'type': 'char', 'length': 40},
                'CLORRES': {'label': 'Result as Originally Received', 'type': 'char', 'length': 200},
                'CLORRESU': {'label': 'Original Units', 'type': 'char', 'length': 40},
                'CLSTRESC': {'label': 'Character Result/Finding', 'type': 'char', 'length': 200},
                'CLSTRESN': {'label': 'Numeric Result/Finding', 'type': 'num', 'length': 8},
                'CLSTRESU': {'label': 'Standard Units', 'type': 'char', 'length': 40},
                'CLSTAT': {'label': 'Completion Status', 'type': 'char', 'length': 40},
                'CLREASND': {'label': 'Reason Not Done', 'type': 'char', 'length': 200},
                'CLDTC': {'label': 'Date/Time of Collection', 'type': 'char', 'length': 19},
                'CLDY': {'label': 'Study Day of Collection', 'type': 'num', 'length': 8},
                'CLTPT': {'label': 'Planned Time Point Name', 'type': 'char', 'length': 40},
                'CLTPTREF': {'label': 'Time Point Reference', 'type': 'char', 'length': 40},
                'CLTPTNUM': {'label': 'Planned Time Point Number', 'type': 'num', 'length': 8},
                'CLELTM': {'label': 'Planned Elapsed Time from Time Point Ref', 'type': 'char', 'length': 20}
            },
            'FW': {
                'FWSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'FWTESTCD': {'label': 'Food/Water Test Short Name', 'type': 'char', 'length': 8},
                'FWTEST': {'label': 'Food/Water Test Name', 'type': 'char', 'length': 40},
                'FWCAT': {'label': 'Category for Food/Water', 'type': 'char', 'length': 40},
                'FWORRES': {'label': 'Result as Originally Received', 'type': 'char', 'length': 200},
                'FWORRESU': {'label': 'Original Units', 'type': 'char', 'length': 40},
                'FWSTRESC': {'label': 'Character Result/Finding', 'type': 'char', 'length': 200},
                'FWSTRESN': {'label': 'Numeric Result/Finding', 'type': 'num', 'length': 8},
                'FWSTRESU': {'label': 'Standard Units', 'type': 'char', 'length': 40},
                'FWSTAT': {'label': 'Completion Status', 'type': 'char', 'length': 40},
                'FWREASND': {'label': 'Reason Not Done', 'type': 'char', 'length': 200},
                'FWDTC': {'label': 'Date/Time of Collection', 'type': 'char', 'length': 19},
                'FWSTDY': {'label': 'Study Day of Start', 'type': 'num', 'length': 8},
                'FWENDY': {'label': 'Study Day of End', 'type': 'num', 'length': 8},
                'FWSTINT': {'label': 'Start Interval', 'type': 'char', 'length': 8},
                'FWENDINT': {'label': 'End Interval', 'type': 'char', 'length': 8}
            },
            'BW': {
                'BWSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'BWTESTCD': {'label': 'Body Weight Test Short Name', 'type': 'char', 'length': 8},
                'BWTEST': {'label': 'Body Weight Test Name', 'type': 'char', 'length': 40},
                'BWORRES': {'label': 'Result as Originally Received', 'type': 'char', 'length': 200},
                'BWORRESU': {'label': 'Original Units', 'type': 'char', 'length': 40},
                'BWSTRESC': {'label': 'Character Result/Finding', 'type': 'char', 'length': 200},
                'BWSTRESN': {'label': 'Numeric Result/Finding', 'type': 'num', 'length': 8},
                'BWSTRESU': {'label': 'Standard Units', 'type': 'char', 'length': 40},
                'BWSTAT': {'label': 'Completion Status', 'type': 'char', 'length': 40},
                'BWREASND': {'label': 'Reason Not Done', 'type': 'char', 'length': 200},
                'VISITNUM': {'label': 'Visit Number', 'type': 'num', 'length': 8},
                'VISIT': {'label': 'Visit Name', 'type': 'char', 'length': 40},
                'VISITDY': {'label': 'Planned Study Day of Visit', 'type': 'num', 'length': 8},
                'BWDTC': {'label': 'Date/Time of Collection', 'type': 'char', 'length': 19},
                'BWDY': {'label': 'Study Day of Collection', 'type': 'num', 'length': 8}
            },
            'OM': {
                'OMSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'OMTESTCD': {'label': 'Organ Measurement Test Short Name', 'type': 'char', 'length': 8},
                'OMTEST': {'label': 'Organ Measurement Test Name', 'type': 'char', 'length': 40},
                'OMCAT': {'label': 'Category for Organ Measurement', 'type': 'char', 'length': 40},
                'OMSCAT': {'label': 'Subcategory for Organ Measurement', 'type': 'char', 'length': 40},
                'OMSPEC': {'label': 'Specimen Type', 'type': 'char', 'length': 40},
                'OMORRES': {'label': 'Result as Originally Received', 'type': 'char', 'length': 200},
                'OMORRESU': {'label': 'Original Units', 'type': 'char', 'length': 40},
                'OMSTRESC': {'label': 'Character Result/Finding', 'type': 'char', 'length': 200},
                'OMSTRESN': {'label': 'Numeric Result/Finding', 'type': 'num', 'length': 8},
                'OMSTRESU': {'label': 'Standard Units', 'type': 'char', 'length': 40},
                'OMSTAT': {'label': 'Completion Status', 'type': 'char', 'length': 40},
                'OMREASND': {'label': 'Reason Not Done', 'type': 'char', 'length': 200},
                'VISITNUM': {'label': 'Visit Number', 'type': 'num', 'length': 8},
                'VISITDY': {'label': 'Planned Study Day of Visit', 'type': 'num', 'length': 8},
                'OMDTC': {'label': 'Date/Time of Collection', 'type': 'char', 'length': 19},
                'OMDY': {'label': 'Study Day of Collection', 'type': 'num', 'length': 8}
            },
            'MA': {
                'MASEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'MASPEC': {'label': 'Specimen Type', 'type': 'char', 'length': 40},
                'MALOC': {'label': 'Location of Finding', 'type': 'char', 'length': 40},
                'MAORRES': {'label': 'Result as Originally Received', 'type': 'char', 'length': 200},
                'MASTRESC': {'label': 'Character Result/Finding', 'type': 'char', 'length': 200},
                'MASEV': {'label': 'Severity/Grade', 'type': 'char', 'length': 20},
                'VISITNUM': {'label': 'Visit Number', 'type': 'num', 'length': 8},
                'VISITDY': {'label': 'Planned Study Day of Visit', 'type': 'num', 'length': 8},
                'MASPID': {'label': 'Sponsor-Defined Identifier', 'type': 'char', 'length': 20}
            },
            'MI': {
                'MISEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'MISPEC': {'label': 'Specimen Type', 'type': 'char', 'length': 40},
                'MILOC': {'label': 'Location of Finding', 'type': 'char', 'length': 40},
                'MIORRES': {'label': 'Result as Originally Received', 'type': 'char', 'length': 200},
                'MISTRESC': {'label': 'Character Result/Finding', 'type': 'char', 'length': 200},
                'MISEV': {'label': 'Severity/Grade', 'type': 'char', 'length': 20},
                'VISITNUM': {'label': 'Visit Number', 'type': 'num', 'length': 8},
                'VISITDY': {'label': 'Planned Study Day of Visit', 'type': 'num', 'length': 8},
                'MISPID': {'label': 'Sponsor-Defined Identifier', 'type': 'char', 'length': 20}
            },
            'CO': {
                'COSEQ': {'label': 'Sequence Number', 'type': 'num', 'length': 8},
                'COREF': {'label': 'Reference', 'type': 'char', 'length': 200},
                'COREFTYPE': {'label': 'Reference Type', 'type': 'char', 'length': 40},
                'COEVAL': {'label': 'Evaluator', 'type': 'char', 'length': 40},
                'COVAL': {'label': 'Comment', 'type': 'char', 'length': 2000},
                'CODTC': {'label': 'Date/Time of Comment', 'type': 'char', 'length': 19},
                'CODY': {'label': 'Study Day of Comment', 'type': 'num', 'length': 8}
            }
        }
        
        # Merge common and domain-specific metadata
        metadata = common_metadata.copy()
        if domain in domain_metadata:
            metadata.update(domain_metadata[domain])
        
        # Return only metadata for columns that exist in the DataFrame
        result = {}
        for col in columns:
            if col in metadata:
                result[col] = metadata[col]
            else:
                # Default metadata for unknown columns
                result[col] = {
                    'label': col,
                    'type': 'char' if col.endswith(('CD', 'DESC', 'DTC', 'NM', 'TXT')) else 'num' if col.endswith(('SEQ', 'NUM', 'DY', 'N')) else 'char',
                    'length': 200 if col.endswith('DESC') else 40
                }
        
        return result

    def validate_csv(self, csv_path, domain):
        """Validate CSV file before conversion"""
        try:
            df = pd.read_csv(csv_path)
            
            # Check if file is empty
            if df.empty:
                raise ValueError(f"CSV file is empty: {csv_path}")
            
            # Check required columns for domain
            required_cols = self.get_required_columns(domain)
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logging.warning(f"Missing required columns for {domain}: {missing_cols}")
            
            # Check STUDYID consistency
            if 'STUDYID' in df.columns:
                unique_studies = df['STUDYID'].nunique()
                if unique_studies > 1:
                    logging.warning(f"Multiple STUDYID values found in {domain}")
            
            # Fix USUBJID format if needed (should be STUDYID-SUBJID)
            if 'USUBJID' in df.columns and 'STUDYID' in df.columns:
                # Check if USUBJID needs fixing
                sample_usubjid = str(df['USUBJID'].iloc[0])
                sample_studyid = str(df['STUDYID'].iloc[0])
                
                if not sample_usubjid.startswith(sample_studyid):
                    logging.info(f"Fixing USUBJID format for {domain}")
                    df['USUBJID'] = df['STUDYID'].astype(str) + '-' + df['USUBJID'].astype(str)
            
            # Check variable name lengths
            long_names = [col for col in df.columns if len(col) > self.max_variable_name_length]
            if long_names:
                logging.warning(f"Variable names > 8 characters in {domain}: {long_names}")
            
            logging.info(f"✓ CSV validation passed for {domain}: {len(df)} records, {len(df.columns)} variables")
            return True, df
            
        except Exception as e:
            logging.error(f"✗ CSV validation failed for {domain}: {str(e)}")
            return False, None
    
    def get_required_columns(self, domain):
        """Get required columns for each SEND domain"""
        common_cols = ['STUDYID', 'DOMAIN']
        
        domain_specific = {
            'TS': ['TSPARMCD', 'TSVAL'],
            'TA': ['ARMCD', 'ARM'],
            'TE': ['ELEMENT'],
            'TX': ['SETCD', 'SET'],
            'DM': ['USUBJID', 'SPECIES', 'STRAIN', 'SEX'],
            'SE': ['USUBJID', 'SESEQ'],
            'DS': ['USUBJID', 'DSSEQ', 'DSTERM'],
            'EX': ['USUBJID', 'EXSEQ'],
            'PC': ['USUBJID', 'PCSEQ', 'PCTESTCD'],
            'PP': ['USUBJID', 'PPSEQ', 'PPTESTCD'],
            'LB': ['USUBJID', 'LBSEQ', 'LBTESTCD'],
            'CL': ['USUBJID', 'CLSEQ', 'CLTESTCD'],
            'FW': ['USUBJID', 'FWSEQ', 'FWTESTCD'],
            'BW': ['USUBJID', 'BWSEQ'],
            'OM': ['USUBJID', 'OMSEQ', 'OMTESTCD'],
            'MA': ['USUBJID', 'MASEQ'],
            'MI': ['USUBJID', 'MISEQ'],
            'CO': ['COSEQ']
        }
        
        return common_cols + domain_specific.get(domain, [])
    
    def prepare_dataframe_for_xpt(self, df, domain):
        """Prepare DataFrame for XPT conversion with proper data types"""
        df_clean = df.copy()
        
        # Ensure DOMAIN column exists and is set correctly
        df_clean['DOMAIN'] = domain.upper()
        
        # Get variable metadata for this domain
        var_metadata = self.get_variable_metadata(domain, df_clean.columns)
        
        # Apply data types and constraints based on metadata
        for col in df_clean.columns:
            if col in var_metadata:
                meta = var_metadata[col]
                
                if meta['type'] == 'num':
                    # Numeric columns - convert to float64 (SAS numeric type)
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
                    df_clean[col] = df_clean[col].fillna(0).astype('float64')
                else:
                    # Character columns
                    df_clean[col] = df_clean[col].astype(str)
                    df_clean[col] = df_clean[col].replace(['nan', 'None', 'NaN'], '')
                    # Truncate to specified length
                    max_length = min(meta.get('length', self.max_string_length), self.max_string_length)
                    df_clean[col] = df_clean[col].str[:max_length]
                    # Remove problematic characters
                    df_clean[col] = df_clean[col].str.replace(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', regex=True)
        
        return df_clean, var_metadata
    
    def convert_csv_to_xpt(self, csv_path, output_dir=None, domain=None):
        """Convert single CSV file to XPT format with proper metadata"""
        
        # Auto-detect domain from filename if not provided
        if domain is None:
            filename = Path(csv_path).stem.upper()
            domain = filename.split('_')[0] if '_' in filename else filename[:2]
        
        if domain not in self.send_domains:
            logging.error(f"Unknown SEND domain: {domain}")
            return False
        
        # Validate CSV
        is_valid, df = self.validate_csv(csv_path, domain)
        if not is_valid:
            return False
        
        # Prepare output directory
        if output_dir is None:
            output_dir = Path(csv_path).parent / 'xpt_files'
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Prepare DataFrame for XPT
        df_clean, var_metadata = self.prepare_dataframe_for_xpt(df, domain)
        
        # Create XPT file
        xpt_filename = f"{domain.upper()}.xpt"
        xpt_path = output_dir / xpt_filename
        
        # Save CSV backup
        csv_backup = output_dir / f"{domain.lower()}_domain_backup.csv"
        df_clean.to_csv(csv_backup, index=False)
        
        try:
            # Prepare variable labels for pyreadstat
            variable_labels = {col: var_metadata[col]['label'][:self.max_label_length] 
                             for col in df_clean.columns if col in var_metadata}
            
            # Write to XPT format using pyreadstat with proper metadata
            pyreadstat.write_xport(
                df_clean, 
                str(xpt_path),
                table_name=domain.upper(),
                file_format_version=5,
            )
            
            logging.info(f"✓ Successfully converted {domain}: {csv_path} → {xpt_path}")
            
            # Validate the created XPT file
            if self.validate_xpt_file(xpt_path, domain):
                logging.info(f"✓ XPT file validation passed for {domain}")
            else:
                logging.warning(f"⚠ XPT file validation failed for {domain}")
            
            return True
            
        except Exception as e:
            logging.error(f"✗ Failed to convert {domain}: {str(e)}")
            return False
    
    def validate_xpt_file(self, xpt_path, domain):
        """Validate generated XPT file"""
        try:
            df_read, meta = pyreadstat.read_xport(str(xpt_path))
            
            logging.info(f"XPT Validation for {domain}:")
            logging.info(f"  Records: {len(df_read)}")
            logging.info(f"  Variables: {len(df_read.columns)}")
            logging.info(f"  Table name: {meta.table_name}")
            logging.info(f"  File size: {os.path.getsize(xpt_path)} bytes")
            
            if len(df_read) == 0:
                logging.warning("XPT file contains no data!")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"XPT validation failed: {str(e)}")
            return False
    
    def convert_all_csvs(self, input_dir, output_dir=None):
        """Convert all SEND CSV files in a directory"""
        
        input_path = Path(input_dir)
        if not input_path.exists():
            logging.error(f"Input directory does not exist: {input_dir}")
            return
        
        if output_dir is None:
            output_dir = input_path / 'xpt_files'
        
        # Find all CSV files
        csv_files = list(input_path.glob('*.csv'))
        if not csv_files:
            logging.warning(f"No CSV files found in {input_dir}")
            return
        
        logging.info(f"Found {len(csv_files)} CSV files to convert")
        
        # Convert each file
        successful_conversions = 0
        failed_conversions = 0
        
        for csv_file in csv_files:
            # Try to detect domain from filename
            filename = csv_file.stem.upper()
            domain = None
            
            # Check if filename contains a known domain
            for known_domain in self.send_domains.keys():
                if known_domain in filename:
                    domain = known_domain
                    break
            
            if not domain:
                # Try first 2 characters
                potential_domain = filename[:2]
                if potential_domain in self.send_domains:
                    domain = potential_domain
            
            if not domain:
                logging.warning(f"Could not detect domain for file: {csv_file}")
                continue
                
            success = self.convert_csv_to_xpt(csv_file, output_dir, domain)
            if success:
                successful_conversions += 1
            else:
                failed_conversions += 1
        
        # Summary
        logging.info(f"\n=== CONVERSION SUMMARY ===")
        logging.info(f"Total files processed: {len(csv_files)}")
        logging.info(f"Successful conversions: {successful_conversions}")
        logging.info(f"Failed conversions: {failed_conversions}")
        
        if output_dir:
            logging.info(f"XPT files saved to: {output_dir}")

def main():
    """Main function for command line usage"""
    converter = SENDConverter()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python csv_to_xpt_converter.py <csv_file_or_directory> [output_directory] [domain]")
        print("  python csv_to_xpt_converter.py single_file.csv")
        print("  python csv_to_xpt_converter.py /path/to/csv/files")
        print("  python csv_to_xpt_converter.py dm_domain.csv xpt_output DM")
        return
    
    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    domain = sys.argv[3] if len(sys.argv) > 3 else None
    
    if os.path.isfile(input_path):
        # Single file conversion
        converter.convert_csv_to_xpt(input_path, output_dir, domain)
    elif os.path.isdir(input_path):
        # Directory conversion
        converter.convert_all_csvs(input_path, output_dir)
    else:
        logging.error(f"Invalid path: {input_path}")

# Example usage functions
def convert_send_study_example():
    """Example: Convert all SEND domains for a specific study"""
    converter = SENDConverter()
    
    # Example: Convert all domains for study 1121-2781
    csv_directory = './send_csv_files'
    output_directory = './send_xpt_files'
    
    converter.convert_all_csvs(csv_directory, output_directory)

def convert_single_domain_example():
    """Example: Convert single domain with explicit domain specification"""
    converter = SENDConverter()
    
    # Convert specific domain
    success = converter.convert_csv_to_xpt(
        csv_path='dm_domain.csv',
        output_dir='xpt_files',
        domain='DM'
    )
    
    if success:
        print("✓ DM domain converted successfully")
    else:
        print("✗ DM domain conversion failed")

if __name__ == "__main__":
    main()