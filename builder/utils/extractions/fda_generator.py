# extraction/fda_generator.py
import logging
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

import pandas as pd
from django.core.files.base import ContentFile
from django.db import transaction

from builder.models import Study, ExtractedDomain, FDAFile, Domain

logger = logging.getLogger(__name__)

class FDAFileGenerator:
    """Generate FDA-required files for SEND submissions"""
    
    def __init__(self, study_id: int):
        self.study_id = study_id
        self.study = Study.objects.get(study_id=study_id)
        self.extracted_domains = ExtractedDomain.objects.filter(study_id=study_id)
    
    def generate_all_files(self) -> Dict[str, Any]:
        """Generate all FDA-required files"""
        try:
            results = {
                "success": True,
                "files_generated": [],
                "errors": []
            }
            
            # Generate define.xml
            define_xml = self._generate_define_xml()
            if define_xml:
                self._save_fda_file("define.xml", define_xml, "text/xml")
                results["files_generated"].append("define.xml")
            
            # Generate study summary
            study_summary = self._generate_study_summary()
            if study_summary:
                self._save_fda_file("study_summary.txt", study_summary, "text/plain")
                results["files_generated"].append("study_summary.txt")
            
            # Generate data specification
            data_spec = self._generate_data_specification()
            if data_spec:
                self._save_fda_file("data_specification.html", data_spec, "text/html")
                results["files_generated"].append("data_specification.html")
            
            # Generate validation report
            validation_report = self._generate_validation_report()
            if validation_report:
                self._save_fda_file("validation_report.html", validation_report, "text/html")
                results["files_generated"].append("validation_report.html")
            
            logger.info(f"Generated {len(results['files_generated'])} FDA files for study {self.study_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error generating FDA files: {e}")
            return {
                "success": False,
                "error": str(e),
                "files_generated": [],
                "errors": [str(e)]
            }
    
    def _generate_define_xml(self) -> Optional[str]:
        """Generate define.xml metadata file"""
        try:
            # Create root element
            root = ET.Element("ODM")
            root.set("xmlns", "http://www.cdisc.org/ns/odm/v1.3")
            root.set("xmlns:def", "http://www.cdisc.org/ns/def/v2.1")
            root.set("xmlns:xlink", "http://www.w3.org/1999/xlink")
            root.set("FileType", "Snapshot")
            root.set("FileOID", f"define_{self.study_id}")
            root.set("CreationDateTime", datetime.now().isoformat())
            
            # Study section
            study_elem = ET.SubElement(root, "Study")
            study_elem.set("OID", f"STUDY_{self.study_id}")
            
            # Global variables
            global_vars = ET.SubElement(study_elem, "GlobalVariables")
            
            study_name = ET.SubElement(global_vars, "StudyName")
            study_name.text = self.study.title or f"Study {self.study_id}"
            
            study_desc = ET.SubElement(global_vars, "StudyDescription")
            study_desc.text = self.study.description or "Toxicology Study"
            
            protocol_name = ET.SubElement(global_vars, "ProtocolName")
            protocol_name.text = f"Protocol_{self.study_id}"
            
            # MetaDataVersion
            metadata_version = ET.SubElement(study_elem, "MetaDataVersion")
            metadata_version.set("OID", "MDV.1")
            metadata_version.set("Name", "Metadata Version 1")
            metadata_version.set("Description", "SEND Metadata")
            metadata_version.set("def:DefineVersion", "2.1")
            metadata_version.set("def:StandardName", "SEND")
            metadata_version.set("def:StandardVersion", "3.1")
            
            # Add domains
            for extracted_domain in self.extracted_domains:
                self._add_domain_to_define(metadata_version, extracted_domain)
            
            # Convert to string
            ET.indent(root, space="  ")
            return ET.tostring(root, encoding="unicode", xml_declaration=True)
            
        except Exception as e:
            logger.error(f"Error generating define.xml: {e}")
            return None
    
    def _add_domain_to_define(self, parent: ET.Element, extracted_domain: ExtractedDomain):
        """Add domain definition to define.xml"""
        domain_code = extracted_domain.domain.code
        
        # ItemGroupDef for the domain
        item_group = ET.SubElement(parent, "ItemGroupDef")
        item_group.set("OID", f"IG.{domain_code}")
        item_group.set("Name", domain_code)
        item_group.set("Repeating", "Yes")
        item_group.set("SASDatasetName", domain_code)
        item_group.set("Domain", domain_code)
        item_group.set("def:Structure", "One record per finding")
        item_group.set("def:Class", "FINDINGS")
        item_group.set("def:ArchiveLocationID", f"LF.{domain_code}")
        
        # Description
        description = ET.SubElement(item_group, "Description")
        desc_text = ET.SubElement(description, "TranslatedText")
        desc_text.set("xml:lang", "en")
        desc_text.text = extracted_domain.domain.description or f"{domain_code} Domain"
        
        # Add variables (columns)
        if extracted_domain.content:
            df = pd.DataFrame(extracted_domain.content)
            for col in df.columns:
                item_ref = ET.SubElement(item_group, "ItemRef")
                item_ref.set("ItemOID", f"IT.{domain_code}.{col}")
                item_ref.set("Mandatory", "Yes" if col in ["STUDYID", "DOMAIN", "USUBJID"] else "No")
    
    def _generate_study_summary(self) -> Optional[str]:
        """Generate study summary text file"""
        try:
            summary_lines = [
                f"STUDY SUMMARY",
                f"=" * 50,
                f"Study ID: {self.study_id}",
                f"Study Title: {self.study.title or 'N/A'}",
                f"Study Description: {self.study.description or 'N/A'}",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "DOMAINS EXTRACTED:",
                "-" * 20
            ]
            
            for extracted_domain in self.extracted_domains:
                domain_code = extracted_domain.domain.code
                record_count = len(extracted_domain.content) if extracted_domain.content else 0
                
                summary_lines.extend([
                    f"{domain_code}: {record_count} records",
                    f"  Description: {extracted_domain.domain.description or 'N/A'}"
                ])
            
            summary_lines.extend([
                "",
                "FILE STRUCTURE:",
                "-" * 15,
                "- define.xml: Metadata definitions",
                "- *.xpt: SAS transport files for each domain",
                "- study_summary.txt: This summary file",
                "- data_specification.html: Detailed data specifications",
                "- validation_report.html: Data validation results"
            ])
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            logger.error(f"Error generating study summary: {e}")
            return None
    
    def _generate_data_specification(self) -> Optional[str]:
        """Generate HTML data specification document"""
        try:
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Data Specification - Study {self.study_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .domain-header {{ background-color: #e6f3ff; font-weight: bold; }}
        .required {{ color: red; }}
    </style>
</head>
<body>
    <h1>Data Specification</h1>
    <h2>Study {self.study_id}: {self.study.title or 'N/A'}</h2>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h3>Overview</h3>
    <p>This document describes the structure and content of the SEND datasets for this study.</p>
    
    <h3>Domain Specifications</h3>
"""
            
            for extracted_domain in self.extracted_domains:
                domain_code = extracted_domain.domain.code
                domain_desc = extracted_domain.domain.description or 'N/A'
                record_count = len(extracted_domain.content) if extracted_domain.content else 0
                
                html_content += f"""
    <h4>{domain_code} - {domain_desc}</h4>
    <p><strong>Records:</strong> {record_count}</p>
    <table>
        <tr>
            <th>Variable</th>
            <th>Label</th>
            <th>Type</th>
            <th>Length</th>
            <th>Required</th>
            <th>Controlled Terms</th>
        </tr>
"""
                
                if extracted_domain.content:
                    df = pd.DataFrame(extracted_domain.content)
                    required_vars = ["STUDYID", "DOMAIN", "USUBJID", f"{domain_code}SEQ"]
                    
                    for col in df.columns:
                        is_required = col in required_vars
                        var_type = "Char" if df[col].dtype == 'object' else "Num"
                        max_length = df[col].astype(str).str.len().max() if not df.empty else 0
                        
                        html_content += f"""
        <tr>
            <td>{col}</td>
            <td>{col}</td>
            <td>{var_type}</td>
            <td>{max_length}</td>
            <td>{'<span class="required">Yes</span>' if is_required else 'No'}</td>
            <td>{self._get_controlled_terms(domain_code, col)}</td>
        </tr>
"""
                
                html_content += "    </table>\n"
            
            html_content += """
</body>
</html>
"""
            return html_content
            
        except Exception as e:
            logger.error(f"Error generating data specification: {e}")
            return None
    
    def _generate_validation_report(self) -> Optional[str]:
        """Generate enhanced HTML validation report with detailed error descriptions"""
        try:
            validation_results = []
            total_records = 0
            total_errors = 0
            total_warnings = 0
            
            # Validate each domain
            for extracted_domain in self.extracted_domains:
                domain_result = self._validate_domain(extracted_domain)
                validation_results.append(domain_result)
                total_records += domain_result['record_count']
                total_errors += len(domain_result['errors'])
                total_warnings += len(domain_result['warnings'])
            
            html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Validation Report - Study {self.study.study_number}</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 20px; 
                line-height: 1.6;
            }}
            .summary {{ 
                background-color: #f9f9f9; 
                padding: 15px; 
                border-radius: 5px; 
                margin: 20px 0; 
                border: 1px solid #ddd;
            }}
            .error {{ color: #d32f2f; font-weight: bold; }}
            .warning {{ color: #f57c00; font-weight: bold; }}
            .success {{ color: #388e3c; font-weight: bold; }}
            table {{ 
                border-collapse: collapse; 
                width: 100%; 
                margin: 20px 0; 
            }}
            th, td {{ 
                border: 1px solid #ddd; 
                padding: 12px; 
                text-align: left; 
            }}
            th {{ 
                background-color: #f2f2f2; 
                font-weight: bold;
            }}
            .issue-detail {{ 
                margin: 15px 0; 
                padding: 15px; 
                border-left: 4px solid #ddd; 
                background-color: #f9f9f9; 
                border-radius: 4px;
            }}
            .error-detail {{ 
                border-left-color: #d32f2f; 
                background-color: #ffebee;
            }}
            .warning-detail {{ 
                border-left-color: #f57c00; 
                background-color: #fff3e0;
            }}
            .rule-id {{ 
                font-weight: bold; 
                color: #1976d2; 
                font-size: 14px;
                margin-bottom: 8px;
            }}
            .examples {{ 
                font-style: italic; 
                color: #666; 
                margin: 8px 0;
                padding: 8px;
                background-color: #f5f5f5;
                border-radius: 3px;
            }}
            .remedy {{ 
                margin-top: 12px; 
                padding: 12px; 
                background-color: #e8f5e8; 
                border-radius: 4px; 
                border-left: 4px solid #4caf50;
            }}
            .collapsible {{ 
                cursor: pointer; 
                padding: 15px; 
                background-color: #e3f2fd; 
                border: 1px solid #2196f3; 
                width: 100%; 
                text-align: left; 
                font-size: 16px;
                font-weight: bold;
                margin: 10px 0;
                border-radius: 4px;
                transition: background-color 0.3s;
            }}
            .collapsible:hover {{
                background-color: #bbdefb;
            }}
            .collapsible.active {{
                background-color: #2196f3;
                color: white;
            }}
            .content {{ 
                display: none; 
                padding: 15px; 
                border: 1px solid #ddd;
                border-top: none;
                background-color: #fafafa;
                margin-bottom: 10px;
            }}
            .content.show {{
                display: block;
            }}
            .domain-header {{
                font-size: 18px;
                margin: 20px 0 10px 0;
                color: #1976d2;
            }}
            .no-issues {{
                color: #388e3c;
                font-style: italic;
                padding: 15px;
                background-color: #e8f5e8;
                border-radius: 4px;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <h1>Enhanced Data Validation Report</h1>
        <h2>Study {self.study.study_number}</h2>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <h3>Summary</h3>
            <p><strong>Total Domains:</strong> {len(validation_results)}</p>
            <p><strong>Total Records:</strong> {total_records}</p>
            <p><strong>Total Errors:</strong> <span class="{'error' if total_errors > 0 else 'success'}">{total_errors}</span></p>
            <p><strong>Total Warnings:</strong> <span class="{'warning' if total_warnings > 0 else 'success'}">{total_warnings}</span></p>
            <p><strong>Overall Status:</strong> <span class="{'success' if total_errors == 0 else 'error'}">{'PASS' if total_errors == 0 else 'FAIL'}</span></p>
        </div>
        
        <h3>Domain Validation Results</h3>
        <table>
            <tr>
                <th>Domain</th>
                <th>Records</th>
                <th>Status</th>
                <th>Errors</th>
                <th>Warnings</th>
            </tr>
    """
            
            for result in validation_results:
                error_count = len(result['errors'])
                warning_count = len(result['warnings'])
                status_class = "success" if error_count == 0 else "error"
                status_text = "PASS" if error_count == 0 else "FAIL"
                
                html_content += f"""
            <tr>
                <td><strong>{result['domain']}</strong></td>
                <td>{result['record_count']}</td>
                <td><span class="{status_class}">{status_text}</span></td>
                <td><span class="{'error' if error_count > 0 else 'success'}">{error_count}</span></td>
                <td><span class="{'warning' if warning_count > 0 else 'success'}">{warning_count}</span></td>
            </tr>
    """
            
            html_content += "    </table>\n"
            
            # Detailed issues section - ALWAYS show, even if no issues
            html_content += "<h3>Detailed Issues</h3>\n"
            
            for result in validation_results:
                domain_name = result['domain']
                error_count = len(result['errors'])
                warning_count = len(result['warnings'])
                
                # Show section for each domain
                html_content += f'<div class="domain-header">Domain: {domain_name}</div>\n'
                
                if error_count == 0 and warning_count == 0:
                    html_content += f'<div class="no-issues">✓ No validation issues found in {domain_name} domain.</div>\n'
                else:
                    # Create collapsible section
                    html_content += f"""
    <button class="collapsible" onclick="toggleContent(this)">
        {domain_name} Issues ({error_count} errors, {warning_count} warnings) - Click to expand
    </button>
    <div class="content">
    """
                    
                    # Show errors first
                    if result['errors']:
                        html_content += f"<h4 style='color: #d32f2f; margin-top: 0;'>Errors ({len(result['errors'])})</h4>\n"
                        
                        for i, error in enumerate(result['errors'], 1):
                            html_content += f"""
        <div class="issue-detail error-detail">
            <div class="rule-id">Error #{i}: {error.get('rule_id', 'N/A')}</div>
            <div style="font-size: 16px; font-weight: bold; margin-bottom: 8px;">{error.get('message', 'Unknown error')}</div>
            <div style="margin-bottom: 8px;">{error.get('description', 'No description available')}</div>
            <div style="margin-bottom: 8px;"><strong>Affected Records:</strong> {error.get('affected_records', 'Unknown')}</div>
    """
                            if error.get('examples'):
                                html_content += f'        <div class="examples"><strong>Examples of invalid data:</strong><br>{error["examples"]}</div>\n'
                            
                            html_content += f"""
            <div class="remedy"><strong>How to Fix:</strong><br>{error.get('remedy', 'No remedy provided')}</div>
        </div>
    """
                    
                    # Show warnings
                    if result['warnings']:
                        html_content += f"<h4 style='color: #f57c00; margin-top: 20px;'>Warnings ({len(result['warnings'])})</h4>\n"
                        
                        for i, warning in enumerate(result['warnings'], 1):
                            html_content += f"""
        <div class="issue-detail warning-detail">
            <div class="rule-id">Warning #{i}: {warning.get('rule_id', 'N/A')}</div>
            <div style="font-size: 16px; font-weight: bold; margin-bottom: 8px;">{warning.get('message', 'Unknown warning')}</div>
            <div style="margin-bottom: 8px;">{warning.get('description', 'No description available')}</div>
            <div style="margin-bottom: 8px;"><strong>Affected Records:</strong> {warning.get('affected_records', 'Unknown')}</div>
    """
                            if warning.get('examples'):
                                html_content += f'        <div class="examples"><strong>Examples:</strong><br>{warning["examples"]}</div>\n'
                            
                            html_content += f"""
            <div class="remedy"><strong>Recommendation:</strong><br>{warning.get('remedy', 'No recommendation provided')}</div>
        </div>
    """
                    
                    html_content += "</div>\n"  # Close content div
            
            # Add JavaScript for collapsible functionality
            html_content += """
    <script>
    function toggleContent(button) {
        button.classList.toggle("active");
        var content = button.nextElementSibling;
        
        if (content.style.display === "block") {
            content.style.display = "none";
            button.innerHTML = button.innerHTML.replace("Click to collapse", "Click to expand");
        } else {
            content.style.display = "block";
            button.innerHTML = button.innerHTML.replace("Click to expand", "Click to collapse");
        }
    }

    // Auto-expand if there are errors
    document.addEventListener('DOMContentLoaded', function() {
        var errorSections = document.querySelectorAll('.collapsible');
        errorSections.forEach(function(button) {
            if (button.innerHTML.includes('errors') && !button.innerHTML.includes('0 errors')) {
                toggleContent(button);
            }
        });
    });
    </script>

    </body>
    </html>
    """
            return html_content
            
        except Exception as e:
            logger.error(f"Error generating enhanced validation report: {e}")
            return None
    
    def _validate_domain(self, extracted_domain: ExtractedDomain) -> Dict[str, Any]:
        """Validate a single domain with detailed error descriptions"""
        domain_code = extracted_domain.domain.code
        errors = []
        warnings = []
        
        try:
            if not extracted_domain.content:
                errors.append({
                    'rule_id': 'SD0001',
                    'severity': 'Error',
                    'message': 'No data found in domain',
                    'description': 'The domain contains no records. Each domain should contain at least one record.',
                    'affected_records': 0,
                    'remedy': 'Extract data for this domain or remove it from the submission.'
                })
                return {
                    'domain': domain_code,
                    'record_count': 0,
                    'errors': errors,
                    'warnings': warnings
                }
            
            df = pd.DataFrame(extracted_domain.content)
            record_count = len(df)
            
            # Check required columns
            required_cols = ["STUDYID", "DOMAIN", "USUBJID"]
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                errors.append({
                    'rule_id': 'SD0002',
                    'severity': 'Error',
                    'message': f'Missing required columns: {", ".join(missing_cols)}',
                    'description': f'Required SEND columns are missing from the {domain_code} domain. These columns must be present in all domains.',
                    'affected_records': record_count,
                    'remedy': f'Add the missing columns: {", ".join(missing_cols)}. Populate with appropriate values or empty strings if data is not available.'
                })
            
            # Check for empty required fields
            for col in required_cols:
                if col in df.columns:
                    empty_mask = df[col].isna() | (df[col].astype(str).str.strip() == '') | (df[col].astype(str).str.lower().isin(['nan', 'none', 'null']))
                    empty_count = empty_mask.sum()
                    if empty_count > 0:
                        errors.append({
                            'rule_id': f'SD000{3 + required_cols.index(col)}',
                            'severity': 'Error',
                            'message': f'Empty values in required column {col}: {empty_count} records',
                            'description': f'Column {col} is required and cannot contain empty, null, or missing values.',
                            'affected_records': empty_count,
                            'remedy': f'Populate all empty {col} values. For STUDYID use study identifier, for DOMAIN use "{domain_code}", for USUBJID use STUDYID-SUBJID format.'
                        })
            
            # Detailed USUBJID format validation
            if 'USUBJID' in df.columns and 'STUDYID' in df.columns:
                usubjid_issues = self._validate_usubjid_format(df, domain_code)
                errors.extend(usubjid_issues['errors'])
                warnings.extend(usubjid_issues['warnings'])
            
            # Check domain consistency
            if 'DOMAIN' in df.columns:
                wrong_domain_mask = df['DOMAIN'] != domain_code
                wrong_domain_count = wrong_domain_mask.sum()
                if wrong_domain_count > 0:
                    wrong_values = df.loc[wrong_domain_mask, 'DOMAIN'].value_counts().to_dict()
                    errors.append({
                        'rule_id': 'SD0010',
                        'severity': 'Error',
                        'message': f'Incorrect DOMAIN values: {wrong_domain_count} records',
                        'description': f'DOMAIN column must contain "{domain_code}" for all records in this domain. Found incorrect values: {wrong_values}',
                        'affected_records': wrong_domain_count,
                        'remedy': f'Change all DOMAIN values to "{domain_code}" in this dataset.'
                    })
            
            # Check STUDYID consistency
            if 'STUDYID' in df.columns:
                studyid_issues = self._validate_studyid_format(df, domain_code)
                errors.extend(studyid_issues['errors'])
                warnings.extend(studyid_issues['warnings'])
            
            # Check sequence numbers
            seq_col = f'{domain_code}SEQ'
            if seq_col in df.columns and 'USUBJID' in df.columns:
                seq_issues = self._validate_sequence_numbers(df, domain_code, seq_col)
                errors.extend(seq_issues['errors'])
                warnings.extend(seq_issues['warnings'])
            
            # Check date formats
            date_cols = [col for col in df.columns if col.endswith('DTC')]
            for date_col in date_cols:
                date_issues = self._validate_date_format(df, date_col, domain_code)
                errors.extend(date_issues['errors'])
                warnings.extend(date_issues['warnings'])
            
            # Domain-specific validations
            domain_specific_issues = self._validate_domain_specific_rules(df, domain_code)
            errors.extend(domain_specific_issues['errors'])
            warnings.extend(domain_specific_issues['warnings'])
            
            return {
                'domain': domain_code,
                'record_count': record_count,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            errors.append({
                'rule_id': 'SD9999',
                'severity': 'Error',
                'message': f'Validation system error: {str(e)}',
                'description': 'An unexpected error occurred during validation.',
                'affected_records': 0,
                'remedy': 'Contact system administrator to resolve validation system issues.'
            })
            return {
                'domain': domain_code,
                'record_count': 0,
                'errors': errors,
                'warnings': warnings
            }
    
    def _get_controlled_terms(self, domain: str, variable: str) -> str:
        """Get controlled terminology for a variable"""
        # This is a simplified version - in practice, you'd have a comprehensive CT database
        ct_map = {
            'SEX': 'M, F',
            'SPECIES': 'RAT, MOUSE, DOG, MONKEY',
            'ROUTE': 'ORAL, IV, SC, IM',
            'CLSEV': 'MINIMAL, MILD, MODERATE, MARKED, SEVERE',
            'MASTRESC': 'NORMAL, ABNORMAL',
            'LBBLFL': 'Y, N'
        }
        
        return ct_map.get(variable, '')
    
    def _save_fda_file(self, filename: str, content: str, content_type: str):
        """Save FDA file to database"""
        try:
            with transaction.atomic():
                fda_file, created = FDAFile.objects.get_or_create(
                    study_id=self.study_id,
                    name=filename,
                    defaults={'file': None}
                )
                
                # Create Django file object
                file_content = ContentFile(content.encode('utf-8'), name=filename)
                fda_file.file.save(filename, file_content, save=True)
                
                logger.info(f"Saved FDA file: {filename}")
                
        except Exception as e:
            logger.error(f"Error saving FDA file {filename}: {e}")
            raise
        
    def _validate_usubjid_format(self, df: pd.DataFrame, domain_code: str) -> Dict[str, List]:
        """Detailed USUBJID format validation"""
        errors = []
        warnings = []
        
        if 'USUBJID' not in df.columns:
            return {'errors': errors, 'warnings': warnings}
        
        # Get expected STUDYID from study object
        expected_studyid = getattr(self.study, 'study_number', 'UNKNOWN')
        expected_pattern = f"{expected_studyid}-"
        
        # Check for invalid USUBJID formats
        usubjid_series = df['USUBJID'].astype(str)
        
        # Find various types of USUBJID issues
        invalid_masks = {
            'missing_studyid_prefix': ~usubjid_series.str.startswith(expected_pattern, na=False),
            'wrong_format': ~usubjid_series.str.match(rf'^{re.escape(expected_studyid)}-\d{{3,}}$', na=False),
            'too_many_dashes': usubjid_series.str.count('-') > 1,
            'empty_subject_part': usubjid_series.str.match(rf'^{re.escape(expected_studyid)}-$', na=False),
            'non_numeric_subject': usubjid_series.str.match(rf'^{re.escape(expected_studyid)}-[^0-9]+', na=False)
        }
        
        # Report specific issues
        for issue_type, mask in invalid_masks.items():
            affected_count = mask.sum()
            if affected_count > 0:
                # Get examples of invalid values
                examples = usubjid_series[mask].unique()[:5].tolist()
                examples_str = ', '.join(examples[:3]) + ('...' if len(examples) > 3 else '')
                
                if issue_type == 'missing_studyid_prefix':
                    errors.append({
                        'rule_id': 'SD0020',
                        'severity': 'Error',
                        'message': f'USUBJID missing study prefix: {affected_count} records',
                        'description': f'USUBJID values must start with study identifier "{expected_studyid}-". Found values that do not start with correct prefix.',
                        'affected_records': affected_count,
                        'examples': examples_str,
                        'remedy': f'Ensure all USUBJID values start with "{expected_studyid}-" followed by subject identifier (e.g., {expected_studyid}-001, {expected_studyid}-002).'
                    })
                
                elif issue_type == 'wrong_format':
                    errors.append({
                        'rule_id': 'SD0021',
                        'severity': 'Error',
                        'message': f'Invalid USUBJID format: {affected_count} records',
                        'description': f'USUBJID must follow pattern "{expected_studyid}-XXX" where XXX is a numeric subject identifier.',
                        'affected_records': affected_count,
                        'examples': examples_str,
                        'remedy': f'Correct format: {expected_studyid}-001, {expected_studyid}-002, etc. Remove extra characters and ensure subject part is numeric.'
                    })
                
                elif issue_type == 'too_many_dashes':
                    errors.append({
                        'rule_id': 'SD0022',
                        'severity': 'Error',
                        'message': f'USUBJID with multiple dashes: {affected_count} records',
                        'description': f'USUBJID should contain exactly one dash separating study ID from subject ID. Found values with multiple dashes.',
                        'affected_records': affected_count,
                        'examples': examples_str,
                        'remedy': f'Remove extra dashes. Format should be: {expected_studyid}-XXX (not {expected_studyid}-XXX-YYY).'
                    })
                
                elif issue_type == 'empty_subject_part':
                    errors.append({
                        'rule_id': 'SD0023',
                        'severity': 'Error',
                        'message': f'USUBJID missing subject identifier: {affected_count} records',
                        'description': f'USUBJID ends with dash but has no subject identifier part.',
                        'affected_records': affected_count,
                        'examples': examples_str,
                        'remedy': f'Add subject identifier after dash (e.g., change "{expected_studyid}-" to "{expected_studyid}-001").'
                    })
                
                elif issue_type == 'non_numeric_subject':
                    errors.append({
                        'rule_id': 'SD0024',
                        'severity': 'Error',
                        'message': f'USUBJID with non-numeric subject ID: {affected_count} records',
                        'description': f'Subject identifier part of USUBJID should be numeric.',
                        'affected_records': affected_count,
                        'examples': examples_str,
                        'remedy': f'Use numeric subject identifiers (e.g., {expected_studyid}-001, not {expected_studyid}-A01).'
                    })
        
        # Check for duplicate USUBJIDs
        duplicated_usubjids = df[df['USUBJID'].duplicated(keep=False)]['USUBJID'].unique()
        if len(duplicated_usubjids) > 0:
            errors.append({
                'rule_id': 'SD0025',
                'severity': 'Error',
                'message': f'Duplicate USUBJID values: {len(duplicated_usubjids)} unique values',
                'description': 'Each USUBJID must be unique across the entire study.',
                'affected_records': df['USUBJID'].duplicated().sum(),
                'examples': ', '.join(duplicated_usubjids[:3].tolist()) + ('...' if len(duplicated_usubjids) > 3 else ''),
                'remedy': 'Ensure each subject has a unique USUBJID. Check for data duplication or incorrect subject numbering.'
            })
        
        return {'errors': errors, 'warnings': warnings}

    def _validate_studyid_format(self, df: pd.DataFrame, domain_code: str) -> Dict[str, List]:
        """Validate STUDYID format"""
        errors = []
        warnings = []
        
        if 'STUDYID' not in df.columns:
            return {'errors': errors, 'warnings': warnings}
        
        expected_studyid = getattr(self.study, 'study_number', 'UNKNOWN')
        
        # Check for inconsistent STUDYID values
        unique_studyids = df['STUDYID'].unique()
        incorrect_studyids = [sid for sid in unique_studyids if str(sid) != expected_studyid]
        
        if incorrect_studyids:
            affected_count = df['STUDYID'].isin(incorrect_studyids).sum()
            errors.append({
                'rule_id': 'SD0030',
                'severity': 'Error',
                'message': f'Incorrect STUDYID values: {affected_count} records',
                'description': f'STUDYID must be "{expected_studyid}" for all records in this study.',
                'affected_records': affected_count,
                'examples': ', '.join(map(str, incorrect_studyids[:3])) + ('...' if len(incorrect_studyids) > 3 else ''),
                'remedy': f'Change all STUDYID values to "{expected_studyid}". Remove any extra numbers or characters.'
            })
        
        # Check for STUDYID format pattern (should be XXXX-XXXX)
        studyid_pattern = r'^\d{4}-\d{4}$'
        if not re.match(studyid_pattern, expected_studyid):
            warnings.append({
                'rule_id': 'SD0031',
                'severity': 'Warning',
                'message': f'STUDYID format may not follow standard pattern',
                'description': f'STUDYID "{expected_studyid}" does not follow the typical XXXX-XXXX format.',
                'affected_records': len(df),
                'remedy': 'Verify that the study identifier format is correct for your organization\'s standards.'
            })
        
        return {'errors': errors, 'warnings': warnings}

    def _validate_sequence_numbers(self, df: pd.DataFrame, domain_code: str, seq_col: str) -> Dict[str, List]:
        """Validate sequence numbers"""
        errors = []
        warnings = []
        
        if seq_col not in df.columns or 'USUBJID' not in df.columns:
            return {'errors': errors, 'warnings': warnings}
        
        # Check for missing sequence numbers
        missing_seq = df[seq_col].isna() | (df[seq_col] == '')
        if missing_seq.any():
            errors.append({
                'rule_id': 'SD0040',
                'severity': 'Error',
                'message': f'Missing sequence numbers: {missing_seq.sum()} records',
                'description': f'Column {seq_col} cannot contain missing values.',
                'affected_records': missing_seq.sum(),
                'remedy': f'Populate {seq_col} with sequential numbers starting from 1 for each USUBJID.'
            })
        
        # Check for duplicate sequence numbers within subjects
        seq_issues = []
        for usubjid in df['USUBJID'].unique():
            subject_data = df[df['USUBJID'] == usubjid]
            seq_values = subject_data[seq_col].dropna()
            
            if seq_values.duplicated().any():
                seq_issues.append(usubjid)
        
        if seq_issues:
            errors.append({
                'rule_id': 'SD0041',
                'severity': 'Error',
                'message': f'Duplicate sequence numbers within subjects: {len(seq_issues)} subjects',
                'description': f'Each subject must have unique {seq_col} values.',
                'affected_records': len(seq_issues),
                'examples': ', '.join(seq_issues[:3]) + ('...' if len(seq_issues) > 3 else ''),
                'remedy': f'Ensure {seq_col} values are sequential and unique within each USUBJID (1, 2, 3, etc.).'
            })
        
        return {'errors': errors, 'warnings': warnings}

    def _validate_date_format(self, df: pd.DataFrame, date_col: str, domain_code: str) -> Dict[str, List]:
        """Validate date format"""
        errors = []
        warnings = []
        
        if date_col not in df.columns:
            return {'errors': errors, 'warnings': warnings}
        
        # Filter out empty dates (which may be acceptable)
        non_empty_dates = df[date_col].dropna()
        non_empty_dates = non_empty_dates[non_empty_dates.astype(str).str.strip() != '']
        
        if non_empty_dates.empty:
            # For DSSTDTC, empty dates might be acceptable
            if date_col == 'DSSTDTC':
                warnings.append({
                    'rule_id': 'SD0050',
                    'severity': 'Warning',
                    'message': f'All {date_col} values are empty',
                    'description': f'{date_col} is conditionally required. Empty values are acceptable when disposition date is unknown.',
                    'affected_records': len(df),
                    'remedy': 'Populate dates where specific disposition timing is known. Leave empty when timing is unspecified.'
                })
            return {'errors': errors, 'warnings': warnings}
        
        # Check ISO date format (YYYY-MM-DD)
        iso_pattern = r'^\d{4}-\d{2}-\d{2}$'
        invalid_dates = []
        
        for date_value in non_empty_dates:
            date_str = str(date_value).strip()
            if not re.match(iso_pattern, date_str):
                invalid_dates.append(date_str)
        
        if invalid_dates:
            unique_invalid = list(set(invalid_dates))
            errors.append({
                'rule_id': 'SD0051',
                'severity': 'Error',
                'message': f'Invalid date format in {date_col}: {len(invalid_dates)} records',
                'description': f'Dates in {date_col} must follow ISO 8601 format (YYYY-MM-DD).',
                'affected_records': len(invalid_dates),
                'examples': ', '.join(unique_invalid[:3]) + ('...' if len(unique_invalid) > 3 else ''),
                'remedy': 'Convert dates to YYYY-MM-DD format (e.g., 2025-03-14, not 03/14/2025 or 14-Mar-2025).'
            })
        
        return {'errors': errors, 'warnings': warnings}

    def _validate_domain_specific_rules(self, df: pd.DataFrame, domain_code: str) -> Dict[str, List]:
        """Domain-specific validation rules"""
        errors = []
        warnings = []
        
        if domain_code == 'DS':
            # DS-specific validations
            if 'DSDECOD' in df.columns:
                valid_dsdecod = ['SCHEDULED SACRIFICE', 'FOUND DEAD', 'MORIBUND SACRIFICE', 'EUTHANIZED', 'ACCIDENTAL DEATH', 'RECOVERED']
                invalid_dsdecod = df[~df['DSDECOD'].isin(valid_dsdecod + [''])]['DSDECOD'].unique()
                
                if len(invalid_dsdecod) > 0:
                    warnings.append({
                        'rule_id': 'SD0060',
                        'severity': 'Warning',
                        'message': f'Non-standard DSDECOD values: {len(invalid_dsdecod)} unique values',
                        'description': 'DSDECOD should use controlled terminology for disposition.',
                        'affected_records': df['DSDECOD'].isin(invalid_dsdecod).sum(),
                        'examples': ', '.join(invalid_dsdecod[:3].tolist()) + ('...' if len(invalid_dsdecod) > 3 else ''),
                        'remedy': f'Use standard terms: {", ".join(valid_dsdecod)}.'
                    })
        
        elif domain_code == 'DM':
            # DM-specific validations
            if 'SEX' in df.columns:
                valid_sex = ['M', 'F', 'U']
                invalid_sex = df[~df['SEX'].isin(valid_sex + [''])]['SEX'].unique()
                
                if len(invalid_sex) > 0:
                    errors.append({
                        'rule_id': 'SD0070',
                        'severity': 'Error',
                        'message': f'Invalid SEX values: {len(invalid_sex)} unique values',
                        'description': 'SEX must be M (Male), F (Female), or U (Unknown).',
                        'affected_records': df['SEX'].isin(invalid_sex).sum(),
                        'examples': ', '.join(invalid_sex[:3].tolist()) + ('...' if len(invalid_sex) > 3 else ''),
                        'remedy': 'Change SEX values to: M, F, or U.'
                    })
        
        return {'errors': errors, 'warnings': warnings}

    