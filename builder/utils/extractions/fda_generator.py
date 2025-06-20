# extraction/fda_generator.py
import logging
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
        """Generate HTML validation report"""
        try:
            validation_results = []
            total_records = 0
            total_errors = 0
            
            # Validate each domain
            for extracted_domain in self.extracted_domains:
                domain_result = self._validate_domain(extracted_domain)
                validation_results.append(domain_result)
                total_records += domain_result['record_count']
                total_errors += len(domain_result['errors'])
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Validation Report - Study {self.study_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
        .error {{ color: red; }}
        .warning {{ color: orange; }}
        .success {{ color: green; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Data Validation Report</h1>
    <h2>Study {self.study_id}</h2>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h3>Summary</h3>
        <p><strong>Total Domains:</strong> {len(validation_results)}</p>
        <p><strong>Total Records:</strong> {total_records}</p>
        <p><strong>Total Issues:</strong> <span class="{'error' if total_errors > 0 else 'success'}">{total_errors}</span></p>
        <p><strong>Overall Status:</strong> <span class="{'success' if total_errors == 0 else 'error'}">{'PASS' if total_errors == 0 else 'FAIL'}</span></p>
    </div>
    
    <h3>Domain Validation Results</h3>
    <table>
        <tr>
            <th>Domain</th>
            <th>Records</th>
            <th>Status</th>
            <th>Issues</th>
        </tr>
"""
            
            for result in validation_results:
                status_class = "success" if len(result['errors']) == 0 else "error"
                status_text = "PASS" if len(result['errors']) == 0 else "FAIL"
                
                html_content += f"""
        <tr>
            <td>{result['domain']}</td>
            <td>{result['record_count']}</td>
            <td><span class="{status_class}">{status_text}</span></td>
            <td>{len(result['errors'])}</td>
        </tr>
"""
            
            html_content += "    </table>\n"
            
            # Detailed issues
            if total_errors > 0:
                html_content += "<h3>Detailed Issues</h3>\n"
                for result in validation_results:
                    if result['errors']:
                        html_content += f"<h4>{result['domain']} Issues</h4>\n<ul>\n"
                        for error in result['errors']:
                            html_content += f"<li class='error'>{error}</li>\n"
                        html_content += "</ul>\n"
            
            html_content += """
</body>
</html>
"""
            return html_content
            
        except Exception as e:
            logger.error(f"Error generating validation report: {e}")
            return None
    
    def _validate_domain(self, extracted_domain: ExtractedDomain) -> Dict[str, Any]:
        """Validate a single domain"""
        domain_code = extracted_domain.domain.code
        errors = []
        
        try:
            if not extracted_domain.content:
                errors.append("No data found in domain")
                return {
                    'domain': domain_code,
                    'record_count': 0,
                    'errors': errors
                }
            
            df = pd.DataFrame(extracted_domain.content)
            
            # Check required columns
            required_cols = ["STUDYID", "DOMAIN", "USUBJID"]
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                errors.append(f"Missing required columns: {', '.join(missing_cols)}")
            
            # Check for empty required fields
            for col in required_cols:
                if col in df.columns:
                    empty_count = df[col].isna().sum() + (df[col] == '').sum()
                    if empty_count > 0:
                        errors.append(f"Empty values in required column {col}: {empty_count} records")
            
            # Check USUBJID format
            if 'USUBJID' in df.columns:
                invalid_usubjid = df[df['USUBJID'].astype(str).str.contains(r'^\d+-\d+', na=False)]
                if not invalid_usubjid.empty:
                    errors.append(f"Invalid USUBJID format: {len(invalid_usubjid)} records")
            
            # Check domain consistency
            if 'DOMAIN' in df.columns:
                wrong_domain = df[df['DOMAIN'] != domain_code]
                if not wrong_domain.empty:
                    errors.append(f"Incorrect DOMAIN values: {len(wrong_domain)} records")
            
            return {
                'domain': domain_code,
                'record_count': len(df),
                'errors': errors
            }
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return {
                'domain': domain_code,
                'record_count': 0,
                'errors': errors
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