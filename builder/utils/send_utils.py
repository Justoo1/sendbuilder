# utils/send_utils.py

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def get_required_columns(domain: str) -> List[str]:
    """
    Get the required columns for a SEND domain according to SENDIG 3.1 standards.
    
    Args:
        domain (str): Domain code
        
    Returns:
        List[str]: List of required column names
    """
    required_columns = {
        # Subject-Level Domains
        'DM': ['STUDYID', 'DOMAIN', 'USUBJID', 'SUBJID', 'RFSTDTC', 'SPECIES', 'STRAIN', 'SEX', 'ARMCD', 'ARM'],
        'DS': ['STUDYID', 'DOMAIN', 'USUBJID', 'DSSEQ', 'DSDECOD', 'DSTERM', 'DSSTDTC'],
        
        # Study Design Domains
        'TS': ['STUDYID', 'DOMAIN', 'TSSEQ', 'TSPARMCD', 'TSPARM', 'TSVAL'],
        'TA': ['STUDYID', 'DOMAIN', 'ARMCD', 'ARM', 'TAETORD', 'ETCD', 'ELEMENT'],
        'TE': ['STUDYID', 'DOMAIN', 'ETCD', 'ELEMENT', 'TESTRL'],
        'TX': ['STUDYID', 'DOMAIN', 'TXSEQ', 'TXPARMCD', 'TXPARM', 'TXVAL'],
        'PP': ['STUDYID', 'DOMAIN', 'PPSEQ', 'PPTESTCD', 'PPTEST'],
        'SE': ['STUDYID', 'DOMAIN', 'USUBJID', 'SESEQ', 'ETCD', 'ELEMENT', 'SESTDTC'],
        
        # Interventions Domains
        'EX': ['STUDYID', 'DOMAIN', 'USUBJID', 'EXSEQ', 'EXTRT', 'EXDOSE', 'EXDOSU', 'EXSTDTC'],
        'PC': ['STUDYID', 'DOMAIN', 'USUBJID', 'PCSEQ', 'PCTESTCD', 'PCTEST', 'PCORRES', 'PCORRESU', 'PCDTC'],
        
        # Findings Domains
        'BW': ['STUDYID', 'DOMAIN', 'USUBJID', 'BWSEQ', 'BWTESTCD', 'BWTEST', 'BWORRES', 'BWORRESU', 'BWDTC'],
        'CL': ['STUDYID', 'DOMAIN', 'USUBJID', 'CLSEQ', 'CLTESTCD', 'CLTEST', 'CLORRES', 'CLSTRESC', 'CLDTC', 'CLCAT', 'CLLOC'],
        'DD': ['STUDYID', 'DOMAIN', 'USUBJID', 'DDSEQ', 'DDTESTCD', 'DDTEST', 'DDORRES', 'DDSTRESC', 'DDDTC'],
        'FW': ['STUDYID', 'DOMAIN', 'USUBJID', 'FWSEQ', 'FWTESTCD', 'FWTEST', 'FWORRES', 'FWORRESU', 'FWDTC'],
        'LB': ['STUDYID', 'DOMAIN', 'USUBJID', 'LBSEQ', 'LBTESTCD', 'LBTEST', 'LBORRES', 'LBORRESU', 'LBSPEC', 'LBDTC'],
        'MA': ['STUDYID', 'DOMAIN', 'USUBJID', 'MASEQ', 'MATESTCD', 'MATEST', 'MAORRES', 'MASTRESC', 'MALOC', 'MADTC'],
        'MI': ['STUDYID', 'DOMAIN', 'USUBJID', 'MISEQ', 'MITESTCD', 'MITEST', 'MIORRES', 'MISTRESC', 'MILOC', 'MIDTC', 'MISEV'],
        'OM': ['STUDYID', 'DOMAIN', 'USUBJID', 'OMSEQ', 'OMTESTCD', 'OMTEST', 'OMORRES', 'OMORRESU', 'OMLOC', 'OMDTC'],
        'PA': ['STUDYID', 'DOMAIN', 'USUBJID', 'PASEQ', 'PATESTCD', 'PATEST', 'PAORRES', 'PASTRESC', 'PALOC', 'PADTC'],
        'PM': ['STUDYID', 'DOMAIN', 'USUBJID', 'PMSEQ', 'PMTESTCD', 'PMTEST', 'PMORRES', 'PMORRESU', 'PMDTC'],
        'EG': ['STUDYID', 'DOMAIN', 'USUBJID', 'EGSEQ', 'EGTESTCD', 'EGTEST', 'EGORRES', 'EGORRESU', 'EGDTC'],
        'CV': ['STUDYID', 'DOMAIN', 'USUBJID', 'CVSEQ', 'CVTESTCD', 'CVTEST', 'CVORRES', 'CVORRESU', 'CVDTC'],
        'VS': ['STUDYID', 'DOMAIN', 'USUBJID', 'VSSEQ', 'VSTESTCD', 'VSTEST', 'VSORRES', 'VSORRESU', 'VSDTC'],
        'CO': ['STUDYID', 'DOMAIN', 'USUBJID', 'COSEQ', 'IDVAR', 'IDVARVAL', 'COREF', 'COEVAL', 'COCOMM'],
    }
    
    # Apply default requirements if not in the map
    if domain not in required_columns:
        logger.warning(f"Domain {domain} not found in required columns map. Using default columns.")
        return ['STUDYID', 'DOMAIN']
    
    return required_columns[domain]

def get_beneficial_optional_columns(domain: str) -> List[str]:
    """
    Get beneficial optional columns that enhance data quality and FDA compliance.
    These are commonly used optional columns that provide valuable analytical information.
    
    Args:
        domain (str): Domain code
        
    Returns:
        List[str]: List of beneficial optional column names
    """
    optional_columns = {
        # Subject-Level Domains
        'DM': ['SITEID', 'AGE', 'AGEU', 'DTHFL', 'DTHDTC', 'COUNTRY', 'ACTARMCD', 'ACTARM'],
        'DS': ['DSCAT', 'DSSCAT', 'DSDY'],
        
        # Study Design Domains  
        'TS': ['TSGRPID', 'TSVALNF', 'TSVALCD'],
        'TA': ['TABRANCH', 'TATRANS'],
        'TE': ['TEENRL', 'TEDUR'],
        'TX': ['SETCD', 'SET'],
        'SE': ['SEENDTC', 'SEDY'],
        
        # Interventions Domains
        'EX': ['EXCAT', 'EXSCAT', 'EXDOSFRM', 'EXDOSFRQ', 'EXROUTE', 'EXLOT', 'EXLOC', 
               'EXENDTC', 'EXSTDY', 'EXENDY'],
        'PC': ['PCCAT', 'PCSCAT', 'PCSTRESC', 'PCSTRESN', 'PCSTRESU', 'PCSPCCND', 
               'PCMETHOD', 'PCDY', 'PCTPT', 'PCTPTNUM', 'PCELTM', 'PCTPTREF', 'PCRFTDTC'],
        
        # Findings Domains
        'BW': ['BWCAT', 'BWSTRESC', 'BWSTRESN', 'BWSTRESU', 'BWSTAT', 'BWREASND', 
               'BWLOC', 'BWMETHOD', 'BWDY', 'BWTPT', 'BWTPTNUM', 'BWELTM', 'BWTPTREF', 'BWRFTDTC'],
        'CL': ['CLSCAT', 'CLORRESU', 'CLSTRESN', 'CLSTRESU', 'CLSTAT', 'CLREASND', 
               'CLMETHOD', 'CLDY', 'CLTPT', 'CLTPTNUM', 'CLELTM', 'CLTPTREF', 'CLRFTDTC', 
               'CLSEV', 'CLDIR'],
        'FW': ['FWCAT', 'FWSTRESC', 'FWSTRESN', 'FWSTRESU', 'FWSTAT', 'FWREASND', 
               'FWMETHOD', 'FWDY', 'FWTPT', 'FWTPTNUM', 'FWELTM', 'FWTPTREF', 'FWRFTDTC'],
        'LB': ['LBCAT', 'LBSCAT', 'LBORNRLO', 'LBORNRHI', 'LBSTRESC', 'LBSTRESN', 'LBSTRESU',
               'LBSTNRLO', 'LBSTNRHI', 'LBNRIND', 'LBSTAT', 'LBREASND', 'LBSPCCND', 'LBSPCUFL',
               'LBMETHOD', 'LBBLFL', 'LBFAST', 'LBDY', 'LBTPT', 'LBTPTNUM', 'LBELTM', 'LBTPTREF', 'LBRFTDTC'],
        'MA': ['MACAT', 'MASCAT', 'MAORRESU', 'MASTRESN', 'MASTRESU', 'MASTAT', 'MAREASND',
               'MADIR', 'MAMETHOD', 'MABLFL', 'MADY'],
        'MI': ['MICAT', 'MISCAT', 'MIORRESU', 'MISTRESN', 'MISTRESU', 'MISTAT', 'MIREASND',
               'MIDIR', 'MIMETHOD', 'MIBLFL', 'MIDY'],
        'OM': ['OMCAT', 'OMSCAT', 'OMSTRESC', 'OMSTRESN', 'OMSTRESU', 'OMSTAT', 'OMREASND',
               'OMDIR', 'OMMETHOD', 'OMBLFL', 'OMDY'],
        'VS': ['VSCAT', 'VSSCAT', 'VSSTRESC', 'VSSTRESN', 'VSSTRESU', 'VSSTAT', 'VSREASND',
               'VSLOC', 'VSMETHOD', 'VSBLFL', 'VSDY', 'VSTPT', 'VSTPTNUM', 'VSELTM', 'VSTPTREF', 'VSRFTDTC'],
        'EG': ['EGCAT', 'EGSCAT', 'EGSTRESC', 'EGSTRESN', 'EGSTRESU', 'EGSTAT', 'EGREASND',
               'EGLOC', 'EGMETHOD', 'EGBLFL', 'EGDY', 'EGTPT', 'EGTPTNUM', 'EGELTM', 'EGTPTREF', 'EGRFTDTC'],
        
        # Special Purpose
        'CO': ['CODTC', 'CODY'],
    }
    
    return optional_columns.get(domain, [])

def get_all_standard_columns(domain: str) -> List[str]:
    """
    Get both required and beneficial optional columns for a domain.
    
    Args:
        domain (str): Domain code
        
    Returns:
        List[str]: List of all standard column names (required + beneficial optional)
    """
    required = get_required_columns(domain)
    optional = get_beneficial_optional_columns(domain)
    
    # Combine and remove duplicates while preserving order
    all_columns = required + [col for col in optional if col not in required]
    
    return all_columns

def get_domain_description(domain: str) -> str:
    """
    Get a description for a SEND domain.
    
    Args:
        domain (str): Domain code
        
    Returns:
        str: Domain description
    """
    descriptions = {
        # Subject-Level Domains
        'DM': 'Demographics - Subject characteristics data such as experimental species, sex, age, and treatment group.',
        'DS': 'Disposition - Completion/discontinuation of subjects in the study.',
        
        # Study Design Domains
        'TS': 'Trial Summary - Trial design characteristics and other attributes.',
        'TA': 'Trial Arms - Planned arms for the study.',
        'TE': 'Trial Elements - Planned elements of the study.',
        'TX': 'Trial Sets - Additional information about the study.',
        'PP': 'Planned Protocols - Planned protocol elements for the study.',
        'SE': 'Subject Elements - Elements associated with each subject in the study.',
        
        # Interventions Domains
        'EX': 'Exposure - Exposure of the subject to the test article.',
        'PC': 'Pharmacokinetic Concentrations - Concentrations of drugs in specimens.',
        
        # Findings Domains
        'BW': 'Body Weights - Weight of the subject.',
        'CL': 'Clinical Observations - Clinical observations of the subject.',
        'DD': 'Death Diagnosis - Cause of death.',
        'FW': 'Food and Water Consumption - Food and water consumption of the subject.',
        'LB': 'Laboratory Test Results - Laboratory test results.',
        'MA': 'Macroscopic Findings - Macroscopic findings from gross pathology.',
        'MI': 'Microscopic Findings - Microscopic findings from histopathology.',
        'OM': 'Organ Measurements - Organ weight measurements.',
        'PA': 'Palpable Masses - Palpable masses observed in the subject.',
        'PM': 'Physical Measurements - Physical measurements other than body weight.',
        'EG': 'ECG Test Results - Electrocardiogram test results.',
        'CV': 'Cardiovascular Test Results - Cardiovascular test results.',
        'VS': 'Vital Signs - Vital signs measurements.',
        'CO': 'Comments - Comments related to a specific variable, record, or dataset.',
    }
    
    return descriptions.get(domain, f"Domain {domain}")

def get_column_description(domain: str, column: str) -> str:
    """
    Get description for a column in a SEND domain according to SENDIG 3.1.
    
    Args:
        domain (str): Domain code
        column (str): Column name
        
    Returns:
        str: Column description
    """
    # Common column descriptions across domains
    common_descriptions = {
        'STUDYID': 'Study Identifier',
        'DOMAIN': 'Domain Abbreviation',
        'USUBJID': 'Unique Subject Identifier',
        'SUBJID': 'Subject Identifier',
        'SPECIES': 'Species',
        'STRAIN': 'Strain/Substrain',
        'SEX': 'Sex',
        'RFSTDTC': 'Subject Reference Start Date/Time',
        'RFENDTC': 'Subject Reference End Date/Time',
        'VISITDY': 'Planned Study Day of Visit',
        'ARMCD': 'Planned Arm Code',
        'ARM': 'Description of Planned Arm',
    }
    
    # Domain-specific column descriptions
    domain_descriptions = {
        'DM': {
            'SITEID': 'Study Site Identifier',
            'AGE': 'Age',
            'AGEU': 'Age Units',
            'DTHFL': 'Death Flag',
            'DTHDTC': 'Date/Time of Death',
            'SVSTDTC': 'Start Date/Time of Schedule Time Point',
            'SVENDTC': 'End Date/Time of Schedule Time Point'
        },
        'DS': {
            'DSSEQ': 'Sequence Number',
            'DSSTDTC': 'Start Date/Time of Disposition',
            'DSDECOD': 'Standardized Disposition Term',
            'DSTERM': 'Reported Term for Disposition',
            'DSDY': 'Study Day of Disposition'
        },
        'TS': {
            'TSSEQ': 'Sequence Number',
            'TSGRPID': 'Group ID',
            'TSPARMCD': 'Trial Summary Parameter Short Name',
            'TSPARM': 'Trial Summary Parameter',
            'TSVAL': 'Parameter Value',
            'TSVALNF': 'Parameter Null Flavor',
            'TSVALCD': 'Parameter Value Code'
        },
        'TA': {
            'TAETORD': 'Element Occurrence Ordinal',
            'ETCD': 'Element Code',
            'ELEMENT': 'Description of Element',
            'TABRANCH': 'Branch',
            'TATRANS': 'Transition Rule'
        },
        'TX': {
            'TXSEQ': 'Sequence Number',
            'TXPARMCD': 'Trial Sets Parameter Short Name',
            'TXPARM': 'Trial Sets Parameter',
            'TXVAL': 'Parameter Value'
        },
        'SE': {
            'SESEQ': 'Sequence Number',
            'ETCD': 'Element Code',
            'ELEMENT': 'Description of Element',
            'SESTDTC': 'Start Date/Time of Element',
            'SEENDTC': 'End Date/Time of Element',
            'SEDY': 'Study Day of Element'
        },
        'BW': {
            'BWSEQ': 'Sequence Number',
            'BWTESTCD': 'Body Weight Test Code',
            'BWTEST': 'Body Weight Test Name',
            'BWORRES': 'Result or Finding in Original Units',
            'BWORRESU': 'Original Units',
            'BWSTRESC': 'Character Result/Finding in Std Format',
            'BWSTRESN': 'Numeric Result/Finding in Standard Units',
            'BWSTRESU': 'Standard Units',
            'BWDTC': 'Date/Time of Measurement',
            'BWDY': 'Study Day of Measurement',
            'BWSTAT': 'Completion Status',
            'BWREASND': 'Reason Measurement Not Done',
            'BWLOC': 'Location of Measurement'
        },
        'CL': {
            'CLSEQ': 'Sequence Number',
            'CLTESTCD': 'Clinical Observation Test Code',
            'CLTEST': 'Clinical Observation Test Name',
            'CLCAT': 'Category for Clinical Observation',
            'CLLOC': 'Location of Clinical Observation',
            'CLORRES': 'Result or Finding in Original Units',
            'CLORRESU': 'Original Units',
            'CLSTRESC': 'Character Result/Finding in Std Format',
            'CLDTC': 'Date/Time of Clinical Observation',
            'CLDY': 'Study Day of Clinical Observation',
            'CLSEV': 'Severity'
        },
        'LB': {
            'LBSEQ': 'Sequence Number',
            'LBTESTCD': 'Laboratory Test Code',
            'LBTEST': 'Laboratory Test Name',
            'LBCAT': 'Category for Lab Test',
            'LBORRES': 'Result or Finding in Original Units',
            'LBORRESU': 'Original Units',
            'LBSPEC': 'Specimen Type',
            'LBBLFL': 'Baseline Flag',
            'LBSTRESC': 'Character Result/Finding in Std Format',
            'LBSTRESN': 'Numeric Result/Finding in Standard Units',
            'LBSTRESU': 'Standard Units',
            'LBDTC': 'Date/Time of Specimen Collection',
            'LBDY': 'Study Day of Specimen Collection',
            'LBSTAT': 'Completion Status',
            'LBREASND': 'Reason Laboratory Test Not Done',
            'LBMETHOD': 'Method of Test',
            'LBNAM': 'Laboratory Name'
        },
        'MA': {
            'MASEQ': 'Sequence Number',
            'MATESTCD': 'Macroscopic Finding Test Code',
            'MATEST': 'Macroscopic Finding Test Name',
            'MAORRES': 'Result or Finding in Original Units',
            'MASTRESC': 'Result or Finding in Standard Format',
            'MALOC': 'Location of the Finding',
            'MADTC': 'Date/Time of Finding',
            'MADY': 'Study Day of Finding',
            'MADIR': 'Directionality',
            'MAMETHOD': 'Method of Test',
            'MASTAT': 'Completion Status',
            'MAREASND': 'Reason Not Done'
        },
        'MI': {
            'MISEQ': 'Sequence Number',
            'MITESTCD': 'Microscopic Finding Test Code',
            'MITEST': 'Microscopic Finding Test Name',
            'MIORRES': 'Result or Finding in Original Units',
            'MISTRESC': 'Result or Finding in Standard Format',
            'MILOC': 'Location of the Finding',
            'MISEV': 'Finding Severity',
            'MIDTC': 'Date/Time of Finding',
            'MIDY': 'Study Day of Finding',
            'MIDIR': 'Directionality',
            'MIMETHOD': 'Method of Test',
            'MISTAT': 'Completion Status',
            'MIREASND': 'Reason Not Done'
        },
        'OM': {
            'OMSEQ': 'Sequence Number',
            'OMTESTCD': 'Organ Measurement Test Code',
            'OMTEST': 'Organ Measurement Test Name',
            'OMORRES': 'Result or Finding in Original Units',
            'OMORRESU': 'Original Units',
            'OMSTRESC': 'Character Result/Finding in Std Format',
            'OMSTRESN': 'Numeric Result/Finding in Standard Units',
            'OMSTRESU': 'Standard Units',
            'OMLOC': 'Location of Measurement',
            'OMDTC': 'Date/Time of Measurement',
            'OMDY': 'Study Day of Measurement',
            'OMSTAT': 'Completion Status',
            'OMREASND': 'Reason Measurement Not Done',
            'OMMETHOD': 'Method of Test'
        },
        'FW': {
            'FWSEQ': 'Sequence Number',
            'FWTESTCD': 'Food/Water Consumption Test Code',
            'FWTEST': 'Food/Water Consumption Test',
            'FWORRES': 'Result or Finding in Original Units',
            'FWORRESU': 'Original Units',
            'FWSTRESC': 'Character Result/Finding in Std Format',
            'FWSTRESN': 'Numeric Result/Finding in Standard Units',
            'FWSTRESU': 'Standard Units',
            'FWDTC': 'Date/Time of Measurement',
            'FWDY': 'Study Day of Measurement',
            'FWSTAT': 'Completion Status',
            'FWREASND': 'Reason Measurement Not Done'
        },
        'EG': {
            'EGSEQ': 'Sequence Number',
            'EGTESTCD': 'ECG Test Code',
            'EGTEST': 'ECG Test Name',
            'EGORRES': 'Result or Finding in Original Units',
            'EGORRESU': 'Original Units',
            'EGSTRESC': 'Character Result/Finding in Std Format',
            'EGSTRESN': 'Numeric Result/Finding in Standard Units',
            'EGSTRESU': 'Standard Units',
            'EGBLFL': 'Baseline Flag',
            'EGDTC': 'Date/Time of ECG',
            'EGDY': 'Study Day of ECG',
            'EGSTAT': 'Completion Status',
            'EGREASND': 'Reason ECG Not Done',
            'EGMETHOD': 'Method of Test'
        },
        'CV': {
            'CVSEQ': 'Sequence Number',
            'CVTESTCD': 'Cardiovascular Test Code',
            'CVTEST': 'Cardiovascular Test Name',
            'CVORRES': 'Result or Finding in Original Units',
            'CVORRESU': 'Original Units',
            'CVSTRESC': 'Character Result/Finding in Std Format',
            'CVSTRESN': 'Numeric Result/Finding in Standard Units',
            'CVSTRESU': 'Standard Units',
            'CVBLFL': 'Baseline Flag',
            'CVDTC': 'Date/Time of Measurement',
            'CVDY': 'Study Day of Measurement',
            'CVSTAT': 'Completion Status',
            'CVREASND': 'Reason Measurement Not Done',
            'CVMETHOD': 'Method of Test'
        },
        'VS': {
            'VSSEQ': 'Sequence Number',
            'VSTESTCD': 'Vital Signs Test Code',
            'VSTEST': 'Vital Signs Test Name',
            'VSORRES': 'Result or Finding in Original Units',
            'VSORRESU': 'Original Units',
            'VSSTRESC': 'Character Result/Finding in Std Format',
            'VSSTRESN': 'Numeric Result/Finding in Standard Units',
            'VSSTRESU': 'Standard Units',
            'VSBLFL': 'Baseline Flag',
            'VSDTC': 'Date/Time of Measurement',
            'VSDY': 'Study Day of Measurement',
            'VSSTAT': 'Completion Status',
            'VSREASND': 'Reason Measurement Not Done',
            'VSMETHOD': 'Method of Test'
        },
        'EX': {
            'EXSEQ': 'Sequence Number',
            'EXTRT': 'Name of Treatment',
            'EXDOSE': 'Dose',
            'EXDOSU': 'Dose Units',
            'EXDOSFRM': 'Dose Form',
            'EXDOSFRQ': 'Dose Frequency',
            'EXROUTE': 'Route of Administration',
            'EXSTDTC': 'Start Date/Time of Treatment',
            'EXENDTC': 'End Date/Time of Treatment',
            'EXSTDY': 'Study Day of Start of Treatment',
            'EXENDY': 'Study Day of End of Treatment'
        },
        'PC': {
            'PCSEQ': 'Sequence Number',
            'PCTESTCD': 'Parameter Short Name',
            'PCTEST': 'Parameter Name',
            'PCORRES': 'Result or Finding in Original Units',
            'PCORRESU': 'Original Units',
            'PCSTRESC': 'Character Result/Finding in Std Format',
            'PCSTRESN': 'Numeric Result/Finding in Standard Units',
            'PCSTRESU': 'Standard Units',
            'PCSPEC': 'Specimen Material Type',
            'PCDTC': 'Date/Time of Specimen Collection',
            'PCDY': 'Study Day of Specimen Collection'
        },
        'CO': {
            'COSEQ': 'Sequence Number',
            'IDVAR': 'Identifying Variable Name',
            'IDVARVAL': 'Identifying Variable Value',
            'COREF': 'Comment Reference',
            'COEVAL': 'Comment Evaluator',
            'COCOMM': 'Comment',
            'CODT': 'Date of Comment',
            'COOBJ': 'Object of Comment'
        },
    }
    
    # Check if column is in common descriptions
    if column in common_descriptions:
        return common_descriptions[column]
    
    # Check if domain has specific descriptions
    if domain in domain_descriptions and column in domain_descriptions[domain]:
        return domain_descriptions[domain][column]
    
    # Default description
    return f"{column} - {domain} Parameter"

def get_codelist_oid(domain: str, column: str) -> Optional[str]:
    """
    Get codelist OID for a column if it uses a controlled terminology.
    
    Args:
        domain (str): Domain code
        column (str): Column name
        
    Returns:
        Optional[str]: Codelist OID or None
    """
    # Common columns that use controlled terminology
    codelist_columns = {
        'SEX': 'CL.SEX',
        'SPECIES': 'CL.SPECIES',
        'STRAIN': 'CL.STRAIN',
        'DOMAIN': 'CL.DOMAIN',
        'ARMCD': 'CL.ARMCD'
    }
    
    # Domain-specific codelists
    domain_codelists = {
        'DS': {
            'DSDECOD': 'CL.DSDECOD'
        },
        'CL': {
            'CLSTRESC': 'CL.CLSTRESC',
            'CLCAT': 'CL.CLCAT',
            'CLLOC': 'CL.CLLOC',
            'CLSEV': 'CL.SEVERITY'
        },
        'BW': {
            'BWSTAT': 'CL.STAT',
            'BWORRESU': 'CL.UNIT',
            'BWSTRESU': 'CL.UNIT'
        },
        'LB': {
            'LBBLFL': 'CL.NY',
            'LBSTAT': 'CL.STAT',
            'LBSPEC': 'CL.SPECIMEN',
            'LBORRESU': 'CL.UNIT',
            'LBSTRESU': 'CL.UNIT'
        },
        'MA': {
            'MASTRESC': 'CL.MASTRESC',
            'MALOC': 'CL.TMLOC',
            'MASTAT': 'CL.STAT'
        },
        'MI': {
            'MISTRESC': 'CL.MISTRESC',
            'MISEV': 'CL.SEVERITY',
            'MILOC': 'CL.TMLOC',
            'MISTAT': 'CL.STAT'
        },
        'OM': {
            'OMSTAT': 'CL.STAT',
            'OMORRESU': 'CL.UNIT',
            'OMSTRESU': 'CL.UNIT',
            'OMLOC': 'CL.TMLOC'
        },
        'FW': {
            'FWSTAT': 'CL.STAT',
            'FWORRESU': 'CL.UNIT',
            'FWSTRESU': 'CL.UNIT'
        },
        'EG': {
            'EGBLFL': 'CL.NY',
            'EGSTAT': 'CL.STAT',
            'EGORRESU': 'CL.UNIT',
            'EGSTRESU': 'CL.UNIT'
        },
        'CV': {
            'CVBLFL': 'CL.NY',
            'CVSTAT': 'CL.STAT',
            'CVORRESU': 'CL.UNIT',
            'CVSTRESU': 'CL.UNIT'
        },
        'VS': {
            'VSBLFL': 'CL.NY',
            'VSSTAT': 'CL.STAT',
            'VSORRESU': 'CL.UNIT',
            'VSSTRESU': 'CL.UNIT'
        },
        'EX': {
            'EXDOSFRQ': 'CL.FREQ',
            'EXROUTE': 'CL.ROUTE'
        }
    }
    
    # Check common codelists
    if column in codelist_columns:
        return codelist_columns[column]
    
    # Check domain-specific codelists
    if domain in domain_codelists and column in domain_codelists[domain]:
        return domain_codelists[domain][column]
    
    # Check for test code columns
    if column.endswith('TESTCD'):
        return f"CL.{domain}{column}"
    
    return None

def get_standard_codelists() -> List[Dict[str, Any]]:
    """
    Get standard codelists according to SENDIG 3.1.
    
    Returns:
        List[Dict[str, Any]]: List of codelist definitions
    """
    return [
        # Yes/No codelist
        {
            'oid': 'CL.NY',
            'name': 'Yes/No Response',
            'datatype': 'text',
            'items': [
                {'coded_value': 'Y', 'display': 'Yes'},
                {'coded_value': 'N', 'display': 'No'}
            ]
        },
        # Sex codelist
        {
            'oid': 'CL.SEX',
            'name': 'Sex',
            'datatype': 'text',
            'items': [
                {'coded_value': 'M', 'display': 'Male'},
                {'coded_value': 'F', 'display': 'Female'},
                {'coded_value': 'U', 'display': 'Unknown'}
            ]
        },
        # Species codelist
        {
            'oid': 'CL.SPECIES',
            'name': 'Species',
            'datatype': 'text',
            'items': [
                {'coded_value': 'RAT', 'display': 'Rat'},
                {'coded_value': 'MOUSE', 'display': 'Mouse'},
                {'coded_value': 'DOG', 'display': 'Dog'},
                {'coded_value': 'PRIMATE', 'display': 'Non-human Primate'},
                {'coded_value': 'RABBIT', 'display': 'Rabbit'},
                {'coded_value': 'GUINEA PIG', 'display': 'Guinea Pig'}
            ]
        },
        # Strain codelist
        {
            'oid': 'CL.STRAIN',
            'name': 'Strain/Substrain',
            'datatype': 'text',
            'items': [
                {'coded_value': 'SD', 'display': 'Sprague Dawley'},
                {'coded_value': 'WIS', 'display': 'Wistar'},
                {'coded_value': 'CD1', 'display': 'CD1'},
                {'coded_value': 'C57BL/6', 'display': 'C57BL/6'},
                {'coded_value': 'BEAGLE', 'display': 'Beagle'},
                {'coded_value': 'NZW', 'display': 'New Zealand White'}
            ]
        },
        # Unit codelist
        {
            'oid': 'CL.UNIT',
            'name': 'Unit',
            'datatype': 'text',
            'items': [
                {'coded_value': 'g', 'display': 'Gram'},
                {'coded_value': 'kg', 'display': 'Kilogram'},
                {'coded_value': 'mg', 'display': 'Milligram'},
                {'coded_value': 'mL', 'display': 'Milliliter'},
                {'coded_value': 'L', 'display': 'Liter'},
                {'coded_value': 'mmHg', 'display': 'Millimeters of Mercury'},
                {'coded_value': 'bpm', 'display': 'Beats per Minute'},
                {'coded_value': '%', 'display': 'Percent'},
                {'coded_value': 'g/day', 'display': 'Grams per Day'},
                {'coded_value': 'mL/day', 'display': 'Milliliters per Day'},
                {'coded_value': 'mmol/L', 'display': 'Millimoles per Liter'},
                {'coded_value': 'U/L', 'display': 'Units per Liter'},
                {'coded_value': 'mg/dL', 'display': 'Milligrams per Deciliter'},
                {'coded_value': 'mg/kg', 'display': 'Milligrams per Kilogram'},
                {'coded_value': 'msec', 'display': 'Milliseconds'},
                {'coded_value': '/min', 'display': 'Per Minute'},
                {'coded_value': 'C', 'display': 'Celsius'},
                {'coded_value': 'F', 'display': 'Fahrenheit'}
            ]
        },
        # Severity codelist
        {
            'oid': 'CL.SEVERITY',
            'name': 'Finding Severity',
            'datatype': 'text',
            'items': [
                {'coded_value': 'MINIMAL', 'display': 'Minimal'},
                {'coded_value': 'MILD', 'display': 'Mild'},
                {'coded_value': 'MODERATE', 'display': 'Moderate'},
                {'coded_value': 'MARKED', 'display': 'Marked'},
                {'coded_value': 'SEVERE', 'display': 'Severe'}
            ]
        },
        # Disposition codelist
        {
            'oid': 'CL.DSDECOD',
            'name': 'Standardized Disposition Term',
            'datatype': 'text',
            'items': [
                {'coded_value': 'SCHEDULED SACRIFICE', 'display': 'Scheduled Sacrifice'},
                {'coded_value': 'FOUND DEAD', 'display': 'Found Dead'},
                {'coded_value': 'MORIBUND SACRIFICE', 'display': 'Moribund Sacrifice'},
                {'coded_value': 'EUTHANIZED', 'display': 'Euthanized'},
                {'coded_value': 'ACCIDENTAL DEATH', 'display': 'Accidental Death'},
                {'coded_value': 'RECOVERED', 'display': 'Recovered'}
            ]
        },
        # Domain codelist
        {
            'oid': 'CL.DOMAIN',
            'name': 'Domain Abbreviation',
            'datatype': 'text',
            'items': [
                {'coded_value': 'DM', 'display': 'Demographics'},
                {'coded_value': 'TS', 'display': 'Trial Summary'},
                {'coded_value': 'TX', 'display': 'Trial Sets'},
                {'coded_value': 'TA', 'display': 'Trial Arms'},
                {'coded_value': 'TE', 'display': 'Trial Elements'},
                {'coded_value': 'SE', 'display': 'Subject Elements'},
                {'coded_value': 'BW', 'display': 'Body Weight'},
                {'coded_value': 'CL', 'display': 'Clinical Observations'},
                {'coded_value': 'DS', 'display': 'Disposition'},
                {'coded_value': 'EX', 'display': 'Exposure'},
                {'coded_value': 'FW', 'display': 'Food and Water Consumption'},
                {'coded_value': 'LB', 'display': 'Laboratory Test Results'},
                {'coded_value': 'MA', 'display': 'Macroscopic Findings'},
                {'coded_value': 'MI', 'display': 'Microscopic Findings'},
                {'coded_value': 'OM', 'display': 'Organ Measurements'},
                {'coded_value': 'PA', 'display': 'Palpable Masses'},
                {'coded_value': 'PC', 'display': 'Pharmacokinetic Concentrations'},
                {'coded_value': 'PM', 'display': 'Physical Measurements'},
                {'coded_value': 'PP', 'display': 'Pharmacokinetic Parameters'},
                {'coded_value': 'EG', 'display': 'ECG Test Results'},
                {'coded_value': 'CV', 'display': 'Cardiovascular Test Results'},
                {'coded_value': 'VS', 'display': 'Vital Signs'}
            ]
        },
        # Specimen codelist
        {
            'oid': 'CL.SPECIMEN',
            'name': 'Specimen Type',
            'datatype': 'text',
            'items': [
                {'coded_value': 'BLOOD', 'display': 'Blood'},
                {'coded_value': 'SERUM', 'display': 'Serum'},
                {'coded_value': 'PLASMA', 'display': 'Plasma'},
                {'coded_value': 'URINE', 'display': 'Urine'},
                {'coded_value': 'CSF', 'display': 'Cerebrospinal Fluid'},
                {'coded_value': 'TISSUE', 'display': 'Tissue'}
            ]
        },
        # Status codelist
        {
            'oid': 'CL.STAT',
            'name': 'Completion Status',
            'datatype': 'text',
            'items': [
                {'coded_value': 'NOT DONE', 'display': 'Not Done'},
                {'coded_value': 'PARTIAL', 'display': 'Partial'},
                {'coded_value': 'COMPLETE', 'display': 'Complete'}
            ]
        },
        # Clinical Observations Category
        {
            'oid': 'CL.CLCAT',
            'name': 'Clinical Observations Category',
            'datatype': 'text',
            'items': [
                {'coded_value': 'GENERAL OBSERVATIONS', 'display': 'General Observations'},
                {'coded_value': 'BEHAVIORAL', 'display': 'Behavioral'},
                {'coded_value': 'DERMATOLOGIC', 'display': 'Dermatologic'},
                {'coded_value': 'NEUROLOGICAL', 'display': 'Neurological'},
                {'coded_value': 'RESPIRATORY', 'display': 'Respiratory'}
            ]
        },
        # Location for Topography
        {
            'oid': 'CL.TMLOC',
            'name': 'Topographical Location',
            'datatype': 'text',
            'items': [
                {'coded_value': 'ABDOMEN', 'display': 'Abdomen'},
                {'coded_value': 'ADRENAL GLAND', 'display': 'Adrenal Gland'},
                {'coded_value': 'BRAIN', 'display': 'Brain'},
                {'coded_value': 'HEART', 'display': 'Heart'},
                {'coded_value': 'KIDNEY', 'display': 'Kidney'},
                {'coded_value': 'LIVER', 'display': 'Liver'},
                {'coded_value': 'LUNG', 'display': 'Lung'},
                {'coded_value': 'SPLEEN', 'display': 'Spleen'},
                {'coded_value': 'THYMUS', 'display': 'Thymus'},
                {'coded_value': 'THYROID', 'display': 'Thyroid Gland'},
                {'coded_value': 'WHOLE BODY', 'display': 'Whole Body'}
            ]
        },
        # Route of Administration
        {
            'oid': 'CL.ROUTE',
            'name': 'Route of Administration',
            'datatype': 'text',
            'items': [
                {'coded_value': 'ORAL', 'display': 'Oral'},
                {'coded_value': 'IV', 'display': 'Intravenous'},
                {'coded_value': 'SC', 'display': 'Subcutaneous'},
                {'coded_value': 'IM', 'display': 'Intramuscular'},
                {'coded_value': 'IP', 'display': 'Intraperitoneal'},
                {'coded_value': 'DERMAL', 'display': 'Dermal'},
                {'coded_value': 'INHAL', 'display': 'Inhalation'},
                {'coded_value': 'GAVAGE', 'display': 'Gavage'}
            ]
        },
        # Frequency
        {
            'oid': 'CL.FREQ',
            'name': 'Frequency',
            'datatype': 'text',
            'items': [
                {'coded_value': 'QD', 'display': 'Once daily'},
                {'coded_value': 'BID', 'display': 'Twice daily'},
                {'coded_value': 'TID', 'display': 'Three times daily'},
                {'coded_value': 'QID', 'display': 'Four times daily'},
                {'coded_value': 'QOD', 'display': 'Every other day'},
                {'coded_value': 'QSHIFT', 'display': 'Once per shift'},
                {'coded_value': 'Q4H', 'display': 'Every 4 hours'},
                {'coded_value': 'Q6H', 'display': 'Every 6 hours'},
                {'coded_value': 'Q8H', 'display': 'Every 8 hours'},
                {'coded_value': 'Q12H', 'display': 'Every 12 hours'},
                {'coded_value': 'QW', 'display': 'Once weekly'}
            ]
        }
    ]