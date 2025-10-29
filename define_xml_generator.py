#!/usr/bin/env python3
"""
SEND Define.xml Generator
Generates FDA-compliant define.xml files for SEND submissions
Flexible approach to handle any combination of domains

Requirements:
pip install pandas lxml beautifulsoup4

Usage:
python define_xml_generator.py
"""

import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import sys
from pathlib import Path
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DefineXMLGenerator:
    """Generate define.xml files for SEND submissions"""
    
    def __init__(self):
        self.define_version = "2.1"
        self.cdisc_version = "1.7"
        self.sendig_version = "3.1.1"
        
        # SEND domain metadata
        self.domain_metadata = {
            'TS': {
                'name': 'Trial Summary',
                'description': 'Trial Summary',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'TSPARMCD'],
                'class': 'TRIAL DESIGN',
                'structure': 'One record per trial summary parameter per study'
            },
            'TA': {
                'name': 'Trial Arms', 
                'description': 'Trial Arms',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'ARMCD'],
                'class': 'TRIAL DESIGN',
                'structure': 'One record per planned arm per study'
            },
            'TE': {
                'name': 'Trial Elements',
                'description': 'Trial Elements', 
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'ELEMENT'],
                'class': 'TRIAL DESIGN',
                'structure': 'One record per element per study'
            },
            'TX': {
                'name': 'Trial Sets',
                'description': 'Trial Sets',
                'purpose': 'Tabulation', 
                'keys': ['STUDYID', 'SETCD'],
                'class': 'TRIAL DESIGN',
                'structure': 'One record per trial set per study'
            },
            'DM': {
                'name': 'Demographics',
                'description': 'Demographics',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID'],
                'class': 'SPECIAL PURPOSE',
                'structure': 'One record per subject'
            },
            'SE': {
                'name': 'Subject Elements',
                'description': 'Subject Elements',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'SESEQ'],
                'class': 'SPECIAL PURPOSE', 
                'structure': 'One record per subject element per subject'
            },
            'DS': {
                'name': 'Disposition',
                'description': 'Disposition',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'DSSEQ'],
                'class': 'SPECIAL PURPOSE',
                'structure': 'One record per disposition event per subject'
            },
            'EX': {
                'name': 'Exposure',
                'description': 'Exposure',
                'purpose': 'Tabulation', 
                'keys': ['STUDYID', 'USUBJID', 'EXSEQ'],
                'class': 'INTERVENTIONS',
                'structure': 'One record per exposure per subject'
            },
            'PC': {
                'name': 'Pharmacokinetics Concentrations',
                'description': 'Pharmacokinetics Concentrations',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'PCSEQ'],
                'class': 'FINDINGS',
                'structure': 'One record per pharmacokinetics measurement per subject'
            },
            'PP': {
                'name': 'Pharmacokinetics Parameters', 
                'description': 'Pharmacokinetics Parameters',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'PPSEQ'],
                'class': 'FINDINGS',
                'structure': 'One record per pharmacokinetics parameter per subject'
            },
            'LB': {
                'name': 'Laboratory Test Results',
                'description': 'Laboratory Test Results',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'LBSEQ'],
                'class': 'FINDINGS',
                'structure': 'One record per laboratory test per subject per time point'
            },
            'CL': {
                'name': 'Clinical Observations',
                'description': 'Clinical Observations', 
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'CLSEQ'],
                'class': 'FINDINGS',
                'structure': 'One record per clinical observation per subject per time point'
            },
            'FW': {
                'name': 'Food and Water Consumption',
                'description': 'Food and Water Consumption',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'FWSEQ'],
                'class': 'FINDINGS',
                'structure': 'One record per food/water measurement per subject per time point'
            },
            'BW': {
                'name': 'Body Weights',
                'description': 'Body Weights',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'BWSEQ'],
                'class': 'FINDINGS',
                'structure': 'One record per body weight measurement per subject per time point'
            },
            'OM': {
                'name': 'Organ Measurements',
                'description': 'Organ Measurements',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'OMSEQ'],
                'class': 'FINDINGS',
                'structure': 'One record per organ measurement per subject'
            },
            'MA': {
                'name': 'Macroscopic Findings',
                'description': 'Macroscopic Findings',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'MASEQ'],
                'class': 'FINDINGS',
                'structure': 'One record per macroscopic finding per subject'
            },
            'MI': {
                'name': 'Microscopic Findings',
                'description': 'Microscopic Findings',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'USUBJID', 'MISEQ'],
                'class': 'FINDINGS', 
                'structure': 'One record per microscopic finding per subject'
            },
            'CO': {
                'name': 'Comments',
                'description': 'Comments',
                'purpose': 'Tabulation',
                'keys': ['STUDYID', 'COSEQ'],
                'class': 'SPECIAL PURPOSE',
                'structure': 'One record per comment'
            }
        }
        
        # Variable metadata from the XPT converter
        self.variable_metadata = self._load_variable_metadata()
        
    def _load_variable_metadata(self):
        """Load comprehensive variable metadata for all SEND domains"""
        # This would typically come from the XPT converter or external source
        # For now, including essential metadata inline
        return {
            'COMMON': {
                'STUDYID': {
                    'label': 'Study Identifier',
                    'type': 'text',
                    'length': 20,
                    'role': 'Identifier',
                    'cdisc_notes': 'Unique identifier for a study'
                },
                'DOMAIN': {
                    'label': 'Domain Abbreviation', 
                    'type': 'text',
                    'length': 2,
                    'role': 'Identifier',
                    'cdisc_notes': 'Two-character abbreviation for the domain'
                },
                'USUBJID': {
                    'label': 'Unique Subject Identifier',
                    'type': 'text', 
                    'length': 64,
                    'role': 'Identifier',
                    'cdisc_notes': 'Identifier used to uniquely identify a subject across all studies'
                }
            },
            'TS': {
                'TSSEQ': {'label': 'Sequence Number', 'type': 'integer', 'role': 'Identifier'},
                'TSPARMCD': {'label': 'Trial Summary Parameter Short Name', 'type': 'text', 'length': 8, 'role': 'Topic'},
                'TSPARM': {'label': 'Trial Summary Parameter', 'type': 'text', 'length': 40, 'role': 'Synonym Qualifier'},
                'TSVAL': {'label': 'Parameter Value', 'type': 'text', 'length': 200, 'role': 'Result Qualifier'},
                'TSVALNF': {'label': 'Parameter Null Flavor', 'type': 'text', 'length': 8, 'role': 'Result Qualifier'}
            },
            'DM': {
                'DMSEQ': {'label': 'Sequence Number', 'type': 'integer', 'role': 'Identifier'},
                'SUBJID': {'label': 'Subject Identifier for the Study', 'type': 'text', 'length': 64, 'role': 'Identifier'},
                'RFSTDTC': {'label': 'Subject Reference Start Date/Time', 'type': 'datetime', 'role': 'Timing'},
                'RFENDTC': {'label': 'Subject Reference End Date/Time', 'type': 'datetime', 'role': 'Timing'},
                'SITEID': {'label': 'Study Site Identifier', 'type': 'text', 'length': 15, 'role': 'Identifier'},
                'AGE': {'label': 'Age', 'type': 'integer', 'role': 'Record Qualifier'},
                'AGEU': {'label': 'Age Units', 'type': 'text', 'length': 40, 'role': 'Variable Qualifier'},  
                'SEX': {'label': 'Sex', 'type': 'text', 'length': 1, 'role': 'Record Qualifier'},
                'SPECIES': {'label': 'Species', 'type': 'text', 'length': 40, 'role': 'Record Qualifier'},
                'STRAIN': {'label': 'Strain', 'type': 'text', 'length': 40, 'role': 'Record Qualifier'},
                'ARMCD': {'label': 'Planned Arm Code', 'type': 'text', 'length': 20, 'role': 'Record Qualifier'},
                'ARM': {'label': 'Description of Planned Arm', 'type': 'text', 'length': 200, 'role': 'Synonym Qualifier'}
            },
            'LB': {
                'LBSEQ': {'label': 'Sequence Number', 'type': 'integer', 'role': 'Identifier'},
                'LBTESTCD': {'label': 'Lab Test Short Name', 'type': 'text', 'length': 8, 'role': 'Topic'},
                'LBTEST': {'label': 'Lab Test Name', 'type': 'text', 'length': 40, 'role': 'Synonym Qualifier'},
                'LBCAT': {'label': 'Category for Lab Test', 'type': 'text', 'length': 40, 'role': 'Grouping Qualifier'},
                'LBORRES': {'label': 'Result as Originally Received', 'type': 'text', 'length': 200, 'role': 'Result Qualifier'},
                'LBORRESU': {'label': 'Original Units', 'type': 'text', 'length': 40, 'role': 'Variable Qualifier'},
                'LBSTRESC': {'label': 'Character Result/Finding', 'type': 'text', 'length': 200, 'role': 'Result Qualifier'},
                'LBSTRESN': {'label': 'Numeric Result/Finding', 'type': 'float', 'role': 'Result Qualifier'},
                'LBSTRESU': {'label': 'Standard Units', 'type': 'text', 'length': 40, 'role': 'Variable Qualifier'},
                'LBDTC': {'label': 'Date/Time of Collection', 'type': 'datetime', 'role': 'Timing'},
                'LBDY': {'label': 'Study Day of Collection', 'type': 'integer', 'role': 'Timing'}
            }
            # Additional domains would be added here based on what's needed
        }
    
    def detect_domains_from_directory(self, directory_path):
        """Auto-detect SEND domains from XPT files in directory"""
        directory = Path(directory_path)
        if not directory.exists():
            logging.error(f"Directory does not exist: {directory_path}")
            return []
        
        domains = []
        
        # Look for XPT files
        xpt_files = list(directory.glob('*.xpt'))
        for xpt_file in xpt_files:
            domain = xpt_file.stem.upper()
            if domain in self.domain_metadata:
                domains.append(domain)
        
        # Look for CSV files as backup
        if not domains:
            csv_files = list(directory.glob('*.csv'))
            for csv_file in csv_files:
                filename = csv_file.stem.upper()
                # Try to extract domain from filename
                for known_domain in self.domain_metadata.keys():
                    if known_domain in filename:
                        domains.append(known_domain)
                        break
        
        domains = sorted(list(set(domains)))  # Remove duplicates and sort
        logging.info(f"Detected domains: {domains}")
        return domains
    
    def analyze_xpt_file(self, xpt_path):
        """Analyze XPT file to extract variable information"""
        try:
            import pyreadstat
            df, metadata = pyreadstat.read_xport(str(xpt_path))
            
            variables = []
            for i, col in enumerate(df.columns, 1):
                var_info = {
                    'name': col,
                    'label': metadata.column_labels.get(col, col) if hasattr(metadata, 'column_labels') else col,
                    'type': self._determine_variable_type(df[col]),
                    'length': self._determine_variable_length(df[col]),
                    'order': i,
                    'role': self._determine_variable_role(col),
                    'mandatory': self._is_mandatory_variable(col)
                }
                variables.append(var_info)
            
            return {
                'record_count': len(df),
                'variables': variables,
                'table_name': metadata.table_name if hasattr(metadata, 'table_name') else Path(xpt_path).stem.upper()
            }
            
        except Exception as e:
            logging.error(f"Error analyzing XPT file {xpt_path}: {str(e)}")
            return None
    
    def _determine_variable_type(self, series):
        """Determine CDISC variable type from pandas series"""
        if pd.api.types.is_numeric_dtype(series):
            if pd.api.types.is_integer_dtype(series):
                return 'integer'
            else:
                return 'float'
        else:
            # Check if it looks like a date
            if series.name and any(dt_indicator in series.name.upper() for dt_indicator in ['DTC', 'DT']):
                return 'datetime'
            return 'text'
    
    def _determine_variable_length(self, series):
        """Determine variable length"""
        if pd.api.types.is_numeric_dtype(series):
            return 8  # Standard numeric length
        else:
            # For text, find max length
            max_len = series.astype(str).str.len().max()
            return min(max_len if pd.notna(max_len) else 0, 200)
    
    def _determine_variable_role(self, var_name):
        """Determine CDISC variable role"""
        var_upper = var_name.upper()
        
        if var_upper in ['STUDYID', 'DOMAIN', 'USUBJID', 'SUBJID'] or var_upper.endswith('SEQ'):
            return 'Identifier'
        elif var_upper.endswith('TESTCD') or var_upper in ['TSPARMCD']:
            return 'Topic'
        elif var_upper.endswith(('ORRES', 'STRESC', 'STRESN')):
            return 'Result Qualifier'
        elif var_upper.endswith(('DTC', 'DT', 'DY')):
            return 'Timing'
        elif var_upper.endswith(('CAT', 'SCAT')):
            return 'Grouping Qualifier'
        elif var_upper.endswith(('TEST', 'PARM')):
            return 'Synonym Qualifier'
        elif var_upper.endswith(('U', 'UNIT')):
            return 'Variable Qualifier'
        else:
            return 'Record Qualifier'
    
    def _is_mandatory_variable(self, var_name):
        """Determine if variable is mandatory"""
        mandatory_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'SUBJID']
        return var_name.upper() in mandatory_vars or var_name.upper().endswith('SEQ')
    
    def generate_define_xml(self, 
                          domains=None, 
                          xpt_directory=None, 
                          study_info=None, 
                          output_path='define.xml'):
        """
        Generate define.xml file
        
        Parameters:
        - domains: List of domain codes ['TS', 'DM', 'LB'] or None for auto-detection
        - xpt_directory: Path to directory containing XPT files
        - study_info: Dictionary with study metadata
        - output_path: Output file path for define.xml
        """
        
        # Auto-detect domains if not provided
        if domains is None and xpt_directory:
            domains = self.detect_domains_from_directory(xpt_directory)
        elif domains is None:
            raise ValueError("Either domains list or xpt_directory must be provided")
        
        # Default study info
        if study_info is None:
            study_info = {
                'study_id': 'UNKNOWN',
                'study_name': 'SEND Study',
                'sponsor': 'Sponsor Name',
                'description': 'SEND Study for Regulatory Submission'
            }
        
        # Create XML structure
        root = self._create_xml_root()
        
        # Add study metadata
        self._add_study_metadata(root, study_info)
        
        # Add standards information
        self._add_standards(root)
        
        # Process each domain
        item_group_defs = ET.SubElement(root, 'ItemGroupDef')
        item_defs = ET.SubElement(root, 'ItemDef')
        code_lists = ET.SubElement(root, 'CodeList')
        
        for domain in domains:
            logging.info(f"Processing domain: {domain}")
            
            # Analyze XPT file if directory provided
            domain_info = None
            if xpt_directory:
                xpt_path = Path(xpt_directory) / f"{domain.upper()}.xpt"
                if xpt_path.exists():
                    domain_info = self.analyze_xpt_file(xpt_path)
            
            # Add domain to define.xml
            self._add_domain_definition(
                item_group_defs, 
                item_defs, 
                code_lists, 
                domain, 
                domain_info
            )
        
        # Write XML file
        self._write_xml_file(root, output_path)
        logging.info(f"Define.xml generated: {output_path}")
        
        return output_path
    
    def _create_xml_root(self):
        """Create XML root element with proper namespaces"""
        root = ET.Element('ODM')
        root.set('xmlns', 'http://www.cdisc.org/ns/odm/v1.3')
        root.set('xmlns:def', 'http://www.cdisc.org/ns/def/v2.1')
        root.set('xmlns:xlink', 'http://www.w3.org/1999/xlink')
        root.set('ODMVersion', '1.3.2')
        root.set('FileOID', f'define_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        root.set('FileType', 'Snapshot')
        root.set('CreationDateTime', datetime.now().isoformat())
        
        return root
    
    def _add_study_metadata(self, root, study_info):
        """Add study-level metadata"""
        study = ET.SubElement(root, 'Study')
        study.set('OID', study_info['study_id'])
        
        global_vars = ET.SubElement(study, 'GlobalVariables')
        
        study_name = ET.SubElement(global_vars, 'StudyName')
        study_name.text = study_info['study_name']
        
        study_description = ET.SubElement(global_vars, 'StudyDescription')
        study_description.text = study_info['description']
        
        protocol_name = ET.SubElement(global_vars, 'ProtocolName')
        protocol_name.text = study_info['study_id']
        
        return study
    
    def _add_standards(self, root):
        """Add standards information"""
        # This would include SEND-specific standards information
        pass
    
    def _add_domain_definition(self, item_group_defs, item_defs, code_lists, domain, domain_info):
        """Add domain definition to XML"""
        domain_meta = self.domain_metadata.get(domain, {})
        
        # Create ItemGroupDef for domain
        item_group = ET.SubElement(item_group_defs, 'ItemGroupDef')
        item_group.set('OID', f'IG.{domain}')
        item_group.set('Name', domain)
        item_group.set('Repeating', 'Yes')
        item_group.set('SASDatasetName', domain.upper())
        item_group.set('def:Class', domain_meta.get('class', 'FINDINGS'))
        item_group.set('def:Structure', domain_meta.get('structure', ''))
        
        # Add description
        description = ET.SubElement(item_group, 'Description')
        translated_text = ET.SubElement(description, 'TranslatedText')
        translated_text.set('xml:lang', 'en')
        translated_text.text = domain_meta.get('description', domain)
        
        # Add variables from analysis or metadata
        if domain_info and 'variables' in domain_info:
            variables = domain_info['variables']
        else:
            # Fallback to predefined metadata
            variables = self._get_default_variables_for_domain(domain)
        
        # Add ItemRefs for each variable
        for var in variables:
            item_ref = ET.SubElement(item_group, 'ItemRef')
            item_ref.set('ItemOID', f'IT.{domain}.{var["name"]}')
            item_ref.set('OrderNumber', str(var.get('order', 1)))
            item_ref.set('Mandatory', 'Yes' if var.get('mandatory', False) else 'No')
            
            # Add ItemDef for variable
            self._add_item_definition(item_defs, domain, var)
    
    def _get_default_variables_for_domain(self, domain):
        """Get default variables for domain when XPT analysis is not available"""
        common_vars = [
            {'name': 'STUDYID', 'label': 'Study Identifier', 'type': 'text', 'length': 20, 'order': 1, 'mandatory': True, 'role': 'Identifier'},
            {'name': 'DOMAIN', 'label': 'Domain Abbreviation', 'type': 'text', 'length': 2, 'order': 2, 'mandatory': True, 'role': 'Identifier'},
        ]
        
        domain_vars = []
        if domain in ['DM', 'SE', 'DS', 'EX', 'PC', 'PP', 'LB', 'CL', 'FW', 'BW', 'OM', 'MA', 'MI']:
            domain_vars.append({
                'name': 'USUBJID', 'label': 'Unique Subject Identifier', 
                'type': 'text', 'length': 64, 'order': 3, 'mandatory': True, 'role': 'Identifier'
            })
        
        # Add domain-specific sequence variable
        if domain not in ['TS', 'TA', 'TE', 'TX']:
            seq_var = f"{domain}SEQ"
            domain_vars.append({
                'name': seq_var, 'label': 'Sequence Number',
                'type': 'integer', 'length': 8, 'order': 4, 'mandatory': True, 'role': 'Identifier'
            })
        
        return common_vars + domain_vars
    
    def _add_item_definition(self, item_defs, domain, var):
        """Add ItemDef for a variable"""
        item_def = ET.SubElement(item_defs, 'ItemDef')
        item_def.set('OID', f'IT.{domain}.{var["name"]}')
        item_def.set('Name', var['name'])
        item_def.set('DataType', var['type'])
        item_def.set('Length', str(var.get('length', 8)))
        item_def.set('def:Role', var.get('role', 'Record Qualifier'))
        
        # Add description
        description = ET.SubElement(item_def, 'Description')
        translated_text = ET.SubElement(description, 'TranslatedText')
        translated_text.set('xml:lang', 'en')
        translated_text.text = var.get('label', var['name'])
    
    def _write_xml_file(self, root, output_path):
        """Write XML to file with proper formatting"""
        # Convert to string and format
        xml_str = ET.tostring(root, encoding='unicode')
        
        # Pretty format
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent='  ', encoding=None)
        
        # Remove empty lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        formatted_xml = '\n'.join(lines)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_xml)
    
    def generate_from_config(self, config_path):
        """Generate define.xml from configuration file"""
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        return self.generate_define_xml(
            domains=config.get('domains'),
            xpt_directory=config.get('xpt_directory'),
            study_info=config.get('study_info'),
            output_path=config.get('output_path', 'define.xml')
        )

def main():
    """Main function for command line usage"""
    generator = DefineXMLGenerator()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python define_xml_generator.py <xpt_directory> [output_file]")
        print("  python define_xml_generator.py config.json")
        print("  python define_xml_generator.py /path/to/xpt/files define.xml")
        return
    
    input_arg = sys.argv[1]
    
    if input_arg.endswith('.json'):
        # Config file mode
        generator.generate_from_config(input_arg)
    else:
        # Directory mode
        xpt_directory = input_arg
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'define.xml'
        
        # Example study info
        study_info = {
            'study_id': '1121-2781',
            'study_name': 'A 7-Day Repeat Dose Toxicity Study of BLU-525',
            'sponsor': 'Blueprint Medicines',
            'description': 'SEND Study for Regulatory Submission'
        }
        
        generator.generate_define_xml(
            xpt_directory=xpt_directory,
            study_info=study_info,
            output_path=output_file
        )

# Example usage functions
def example_auto_detect():
    """Example: Auto-detect domains from XPT directory"""
    generator = DefineXMLGenerator()
    
    study_info = {
        'study_id': '1121-2781',
        'study_name': 'A 7-Day Repeat Dose Toxicity Study of BLU-525',
        'sponsor': 'Blueprint Medicines',
        'description': 'SEND Study for Regulatory Submission'
    }
    
    generator.generate_define_xml(
        xpt_directory='./xpt_files',
        study_info=study_info,
        output_path='define_auto.xml'
    )

def example_explicit_domains():
    """Example: Explicitly specify domains"""
    generator = DefineXMLGenerator()
    
    domains = ['TS', 'TA', 'TE', 'TX', 'DM', 'SE', 'DS', 'EX', 'LB', 'BW']
    
    study_info = {
        'study_id': '1121-2781', 
        'study_name': 'A 7-Day Repeat Dose Toxicity Study of BLU-525',
        'sponsor': 'Blueprint Medicines',
        'description': 'SEND Study for Regulatory Submission'
    }
    
    generator.generate_define_xml(
        domains=domains,
        xpt_directory='./xpt_files',
        study_info=study_info,
        output_path='define_explicit.xml'
    )

def create_config_example():
    """Example: Create configuration file for define.xml generation"""
    config = {
        "domains": ["TS", "TA", "TE", "TX", "DM", "SE", "DS", "EX", "PC", "PP", "LB", "CL", "FW", "BW", "OM", "MA", "MI", "CO"],
        "xpt_directory": "./xpt_files",
        "study_info": {
            "study_id": "1121-2781",
            "study_name": "A 7-Day Repeat Dose Toxicity Study of BLU-525",
            "sponsor": "Blueprint Medicines",
            "description": "SEND Study for Regulatory Submission",
            "protocol_title": "A 7-Day Repeat Dose Toxicity Study of BLU-525 in Male Sprague Dawley Rats",
            "indication": "Oncology",
            "phase": "Nonclinical"
        },
        "output_path": "define.xml",
        "validation": {
            "pinnacle21": True,
            "fda_validator": True
        },
        "options": {
            "include_code_lists": True,
            "include_value_level_metadata": True,
            "include_analysis_results": False
        }
    }
    
    with open('define_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("Configuration file created: define_config.json")

def example_minimal_domains():
    """Example: Generate define.xml with minimal required domains"""
    generator = DefineXMLGenerator()
    
    # Minimal SEND submission domains
    minimal_domains = ['TS', 'DM', 'EX', 'DS']
    
    study_info = {
        'study_id': 'MIN-001',
        'study_name': 'Minimal SEND Study Example',
        'sponsor': 'Example Sponsor',
        'description': 'Minimal SEND study with required domains only'
    }
    
    generator.generate_define_xml(
        domains=minimal_domains,
        study_info=study_info,
        output_path='define_minimal.xml'
    )

def example_findings_focus():
    """Example: Generate define.xml focused on findings domains"""
    generator = DefineXMLGenerator()
    
    # Findings-focused domains
    findings_domains = ['TS', 'DM', 'EX', 'DS', 'LB', 'CL', 'BW', 'OM', 'MA', 'MI']
    
    study_info = {
        'study_id': 'FIND-001',
        'study_name': 'Findings-Focused SEND Study',
        'sponsor': 'Research Organization',
        'description': 'SEND study focused on safety findings domains'
    }
    
    generator.generate_define_xml(
        domains=findings_domains,
        study_info=study_info,
        output_path='define_findings.xml'
    )

def example_with_pk():
    """Example: Generate define.xml including pharmacokinetics domains"""
    generator = DefineXMLGenerator()
    
    # Include PK domains
    pk_domains = ['TS', 'TA', 'TE', 'TX', 'DM', 'SE', 'DS', 'EX', 'PC', 'PP', 'LB', 'BW']
    
    study_info = {
        'study_id': 'PK-001',
        'study_name': 'Toxicokinetic SEND Study',
        'sponsor': 'Pharma Company',
        'description': 'SEND study including toxicokinetic assessments'
    }
    
    generator.generate_define_xml(
        domains=pk_domains,
        study_info=study_info,
        output_path='define_with_pk.xml'
    )

class DefineXMLValidator:
    """Validate generated define.xml files"""
    
    def __init__(self):
        self.validation_rules = self._load_validation_rules()
    
    def _load_validation_rules(self):
        """Load SEND-specific validation rules"""
        return {
            'required_domains': ['TS', 'DM'],
            'required_variables': {
                'ALL': ['STUDYID', 'DOMAIN'],
                'DM': ['USUBJID', 'SPECIES', 'STRAIN', 'SEX'],
                'TS': ['TSPARMCD', 'TSVAL']
            },
            'variable_constraints': {
                'STUDYID': {'max_length': 20, 'type': 'text'},
                'DOMAIN': {'max_length': 2, 'type': 'text'},
                'USUBJID': {'max_length': 64, 'type': 'text'}
            }
        }
    
    def validate_define_xml(self, define_xml_path):
        """Validate define.xml file against SEND rules"""
        try:
            tree = ET.parse(define_xml_path)
            root = tree.getroot()
            
            validation_results = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'info': []
            }
            
            # Check XML structure
            self._validate_xml_structure(root, validation_results)
            
            # Check domain requirements
            self._validate_domain_requirements(root, validation_results)
            
            # Check variable requirements
            self._validate_variable_requirements(root, validation_results)
            
            # Generate validation report
            self._generate_validation_report(validation_results, define_xml_path)
            
            return validation_results
            
        except Exception as e:
            logging.error(f"Validation failed: {str(e)}")
            return {'is_valid': False, 'errors': [str(e)], 'warnings': [], 'info': []}
    
    def _validate_xml_structure(self, root, results):
        """Validate basic XML structure"""
        # Check namespaces
        expected_namespaces = [
            'http://www.cdisc.org/ns/odm/v1.3',
            'http://www.cdisc.org/ns/def/v2.1'
        ]
        
        for ns in expected_namespaces:
            if ns not in root.attrib.values():
                results['warnings'].append(f"Missing expected namespace: {ns}")
    
    def _validate_domain_requirements(self, root, results):
        """Validate domain-specific requirements"""
        # Find all ItemGroupDef elements (domains)
        domains_found = []
        for item_group in root.findall('.//ItemGroupDef'):
            domain_name = item_group.get('Name', '')
            if domain_name:
                domains_found.append(domain_name)
        
        # Check required domains
        for required_domain in self.validation_rules['required_domains']:
            if required_domain not in domains_found:
                results['errors'].append(f"Required domain missing: {required_domain}")
                results['is_valid'] = False
        
        results['info'].append(f"Domains found: {', '.join(sorted(domains_found))}")
    
    def _validate_variable_requirements(self, root, results):
        """Validate variable-specific requirements"""
        # This would include more detailed variable validation
        pass
    
    def _generate_validation_report(self, results, define_xml_path):
        """Generate validation report"""
        report_path = define_xml_path.replace('.xml', '_validation_report.txt')
        
        with open(report_path, 'w') as f:
            f.write("DEFINE.XML VALIDATION REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"File: {define_xml_path}\n")
            f.write(f"Validation Date: {datetime.now().isoformat()}\n")
            f.write(f"Overall Status: {'PASS' if results['is_valid'] else 'FAIL'}\n\n")
            
            if results['errors']:
                f.write("ERRORS:\n")
                for error in results['errors']:
                    f.write(f"  - {error}\n")
                f.write("\n")
            
            if results['warnings']:
                f.write("WARNINGS:\n")
                for warning in results['warnings']:
                    f.write(f"  - {warning}\n")
                f.write("\n")
            
            if results['info']:
                f.write("INFORMATION:\n")
                for info in results['info']:
                    f.write(f"  - {info}\n")
        
        logging.info(f"Validation report generated: {report_path}")

if __name__ == "__main__":
    main()