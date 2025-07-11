"""
SEND Domain Validation Utilities

This module provides specialized validation functions for different SEND domains
to reduce false positives and improve accuracy of domain detection.
"""

import re
from typing import List, Tuple, Dict, Any


class DomainValidator:
    """Utility class for domain-specific validation logic"""
    
    # Add these as class constants
    PROTOCOL_KEYWORDS = [
        'protocol', 'amendment', 'objective', 'methodology', 'procedures will be',
        'animals will be', 'study design', 'shall be', 'will be performed'
    ]

    DATA_TABLE_PATTERNS = [
        r'Table\s+\d+:',
        r'Animal\s+\d+.*\d+',
        r'Group\s+\d+.*\d+',
        r'Subject\s+\d+.*\d+'
    ]
    
    @staticmethod
    def validate_vital_signs(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        """
        Validate VS (Vital Signs) domain detection
        
        Args:
            content: Page content to validate
            initial_confidence: Initial confidence score
            evidence: List of evidence strings
            
        Returns:
            Tuple of (adjusted_confidence, updated_evidence)
        """
        confidence = initial_confidence
        
        # Check for actual vital signs measurements
        actual_vs_indicators = [
            r'\d+\.?\d*\s*(bpm|beats?\s*per\s*minute)',  # Heart rate
            r'\d+\.?\d*\s*°[CF]',  # Temperature  
            r'\d+/\d+\s*mmHg',  # Blood pressure
            r'heart\s*rate:?\s*\d+',  # Heart rate with label
            r'temperature:?\s*\d+',  # Temperature with label
            r'pulse:?\s*\d+',  # Pulse with label
            r'respiratory\s*rate:?\s*\d+',  # Respiratory rate
        ]
        
        actual_vs_found = any(re.search(pattern, content, re.IGNORECASE) 
                             for pattern in actual_vs_indicators)
        
        # Heavy penalty if no actual measurements found
        if not actual_vs_found:
            confidence = max(0, confidence - 60)
            evidence.append("Penalized: No actual vital signs measurements found")
        
        # Protocol/methodology penalty
        methodology_indicators = [
            r'(?i)protocol',
            r'(?i)study.{0,10}design',
            r'(?i)methodology',
            r'(?i)procedures?.{0,20}will.{0,20}be',
            r'(?i)animals?.{0,20}will.{0,20}be.{0,20}observed',
            r'(?i)amendment',
            r'(?i)objective',
            r'(?i)test.{0,20}facility',
            r'(?i)dose.{0,20}formulation',
            r'(?i)administration',
        ]
        
        methodology_count = sum(1 for pattern in methodology_indicators 
                               if re.search(pattern, content, re.IGNORECASE))
        
        if methodology_count >= 2:  # Multiple methodology indicators
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: VS patterns found in protocol/methodology context")
        
        # Clinical observations context penalty
        if re.search(r'clinical.{0,20}observ', content, re.IGNORECASE):
            confidence = max(0, confidence - 40)
            evidence.append("Penalized: VS patterns found in clinical observations context")

        
        actual_vs_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in actual_vs_indicators)
        
        # Heavy penalty if no actual measurements found
        if not actual_vs_found:
            confidence = max(0, confidence - 60)
            evidence.append("Penalized: No actual vital signs measurements found")
        
        # Methodology/protocol penalty
        methodology_terms = [
            'procedures', 'methodology', 'protocol', 'will be', 
            'shall be', 'administered', 'formulation'
        ]
        
        methodology_count = sum(1 for term in methodology_terms 
                            if term.lower() in content.lower())
        
        if methodology_count >= 3:
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: Appears to be methodology/protocol text")
        
        return confidence, evidence
    
    @staticmethod
    def validate_clinical_observations(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        """
        Validate CL (Clinical) domain detection
        
        Args:
            content: Page content to validate
            initial_confidence: Initial confidence score
            evidence: List of evidence strings
            
        Returns:
            Tuple of (adjusted_confidence, updated_evidence)
        """
        confidence = initial_confidence
        
        # Check for actual clinical data vs methodology
        actual_cl_indicators = [
            r'Animal\s+\d+',  # Individual animal IDs
            r'Group\s+\d+.*:\s*\d+',  # Group summaries with counts
            r'(Normal|Activity|Salivation|Squinting|Hypoactive|Lethargic).*\d+',  # Clinical findings with counts
            r'\d+\s+\d+\s+\d+\s*\.',  # Data tables with numbers
            r'X\s*\.\s*X',  # Clinical observation notation
            r'Table\s+\d+:.*Clinical\s+Observations',  # Clinical observation tables
            r'Animal\s+\d+.*[XH]',  # Animal data with X or H markers
        ]
        
        actual_cl_found = any(re.search(pattern, content, re.IGNORECASE) 
                             for pattern in actual_cl_indicators)
        
        # Heavy penalty if no actual clinical data found
        if not actual_cl_found:
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: No actual clinical data tables found")
        
        # Protocol/methodology penalty
        methodology_indicators = [
            r'(?i)at\s+minimum.*will\s+be\s+observed',
            r'(?i)protocol.*section',
            r'(?i)amendment',
            r'(?i)table\s+of\s+contents',
            r'(?i)deviation',
            r'(?i)procedures.*will\s+be',
            r'(?i)methodology',
            r'(?i)study\s+design',
            r'(?i)objective',
        ]
        
        methodology_count = sum(1 for pattern in methodology_indicators 
                               if re.search(pattern, content, re.IGNORECASE))
        
        if methodology_count >= 1:
            confidence = max(0, confidence - 60)
            evidence.append("Penalized: Appears to be methodology/protocol text")
        
        # Administrative/summary penalty
        admin_indicators = [
            r'(?i)table\s+of\s+contents',
            r'(?i)summary',
            r'(?i)conclusion',
            r'(?i)reference',
            r'(?i)abbreviation',
        ]
        
        admin_count = sum(1 for pattern in admin_indicators 
                         if re.search(pattern, content, re.IGNORECASE))
        
        if admin_count >= 1:
            confidence = max(0, confidence - 30)
            evidence.append("Penalized: Appears to be administrative/summary text")
        
        return confidence, evidence
    
    @staticmethod
    def validate_demographics(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        """
        Enhanced DM (Demographics) domain validation
        """
        confidence = initial_confidence
        
        # Check for actual demographic data tables
        actual_dm_indicators = [
            r'Subject\s+\d+.*\d+.*(?:Male|Female|M|F)',  # Subject with age/weight and sex
            r'Animal\s+\d+.*\d+\.?\d*\s*(?:g|kg).*(?:Male|Female|M|F)',  # Animal with weight and sex
            r'Group\s+\d+.*\d+\s*(?:Male|Female).*\d+\s*(?:Male|Female)',  # Group demographics
            r'Randomization.*Animal.*Group',  # Randomization tables
            r'Table.*Demographics.*Data',  # Demographics data tables
            r'Age.*Weight.*Sex.*Group',  # Demographics table headers
            r'\d+\s+weeks.*\d+\s*g.*(?:Male|Female)',  # Age, weight, sex data
        ]
        
        actual_dm_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in actual_dm_indicators)
        
        if not actual_dm_found:
            confidence = max(0, confidence - 55)
            evidence.append("Penalized: No actual demographic data tables found")
        
        # Heavy penalty for protocol/methodology content
        methodology_indicators = [
            r'(?i)animals?\s+will\s+be\s+randomized',
            r'(?i)males?\s+and\s+females?\s+were\s+chosen',
            r'(?i)age\s+at\s+receipt',
            r'(?i)weight\s+on\s+dosing',
            r'(?i)nulliparous\s+and\s+nonpregnant',
            r'(?i)approximate\s+age\s+and\s+weight',
            r'(?i)randomization.*procedure',
            r'(?i)test\s+system.*species',
        ]
        
        methodology_count = sum(1 for pattern in methodology_indicators 
                            if re.search(pattern, content, re.IGNORECASE))
        
        if methodology_count >= 2:
            confidence = max(0, confidence - 65)
            evidence.append("Penalized: Appears to be demographics methodology/protocol text")
        
        return confidence, evidence

    @staticmethod
    def validate_body_weight(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        """
        Enhanced BW (Body Weight) domain validation
        """
        confidence = initial_confidence
        
        # Check for actual body weight DATA tables (not just mentions)
        actual_bw_indicators = [
            r'Table\s+\d+:.*Body\s*Weight.*Data',  # Specific BW table titles
            r'Individual.*Body\s*Weight.*Data',  # Individual BW tables
            r'Summary.*Body\s*Weight.*Data',  # Summary BW tables
            r'Animal\s+\d+.*\d+\.?\d*\s+\d+\.?\d*\s+\d+\.?\d*',  # Multiple weight measurements per animal
            r'Day.*Body\s*Weight.*Grams',  # Table headers with days and weights
            r'\d{4}\s+\d{3,4}\.\d+\s+\d{3,4}\.\d+',  # Animal ID with multiple weights
            r'Mean.*\d+\.?\d*.*SD.*\d+\.?\d*.*N\s+\d+',  # Statistical summaries of weights
        ]
        
        actual_bw_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in actual_bw_indicators)
        
        if not actual_bw_found:
            confidence = max(0, confidence - 60)
            evidence.append("Penalized: No actual body weight data tables found")
        
        # Heavy penalty for protocol weight specifications
        protocol_weight_indicators = [
            r'(?i)at\s+least\s+\d+\s*g.*(?:males?|females?)',  # "at least 240 g (males)"
            r'(?i)weight\s+on\s+dosing.*at\s+least',
            r'(?i)approximate.*weight.*receipt',
            r'(?i)body\s*weights?\s*will\s*be\s*recorded',
            r'(?i)minimum.*body\s*weight',
            r'(?i)test\s+system.*weight',
        ]
        
        protocol_count = sum(1 for pattern in protocol_weight_indicators 
                            if re.search(pattern, content, re.IGNORECASE))
        
        if protocol_count >= 1:
            confidence = max(0, confidence - 70)
            evidence.append("Penalized: Contains protocol body weight specifications, not data")
        
        # Penalty for isolated weight mentions without data context
        isolated_weight_pattern = r'\b\d+\.?\d*\s*g\b'
        data_context_patterns = [
            r'Day\s+\d+',
            r'Animal\s+\d+',
            r'Table\s+\d+',
            r'Mean.*SD',
            r'Group\s+\d+'
        ]
        
        has_weights = bool(re.search(isolated_weight_pattern, content))
        has_data_context = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in data_context_patterns)
        
        if has_weights and not has_data_context:
            confidence = max(0, confidence - 40)
            evidence.append("Penalized: Weight mentions without data table context")
        
        return confidence, evidence
    
    @staticmethod
    def validate_exposure(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        """
        Enhanced EX (Exposure) domain validation
        """
        confidence = initial_confidence
        
        # Check for actual DOSING/ADMINISTRATION data (not just dose mentions)
        actual_ex_indicators = [
            r'Table\s+\d+:.*(?:Dose|Dosing|Administration)',  # Actual dosing tables
            r'Individual.*(?:Dose|Dosing).*Data',  # Individual dosing data
            r'Dose\s+Formulation.*Analysis',  # Dose formulation tables
            r'Administration.*\d{2}/\d{2}/\d{2}.*\d{1,2}:\d{2}',  # Actual administration records with dates/times
            r'Animal\s+\d+.*administered.*\d+\.?\d*\s*mg/kg',  # Individual animal dosing records
            r'Formulation.*Concentration.*Volume',  # Dosing formulation details
            r'Route.*Frequency.*Duration',  # Administration details
            r'Test\s+Article.*Vehicle.*Prepared',  # Actual preparation records
        ]
        
        actual_ex_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in actual_ex_indicators)
        
        if not actual_ex_found:
            confidence = max(0, confidence - 65)
            evidence.append("Penalized: No actual dosing/administration data found")
        
        # Heavy penalty for experimental design dose specifications (not actual dosing data)
        design_dose_indicators = [
            r'(?i)experimental\s+design.*\d+\s*mg/kg',  # Design tables with doses
            r'(?i)group\s+\d+.*treatment.*\d+\s*mg/kg.*number\s+of\s+animals',  # Design group tables
            r'(?i)dose\s+level.*dose\s+concentration.*number\s+of\s+animals',  # Protocol design tables
            r'(?i)justification\s+of\s+dose',
            r'(?i)route\s+of\s+administration\s+will\s+be',
            r'(?i)dose\s+selection.*will\s+be\s+based',
        ]
        
        design_count = sum(1 for pattern in design_dose_indicators 
                        if re.search(pattern, content, re.IGNORECASE))
        
        if design_count >= 1:
            confidence = max(0, confidence - 75)
            evidence.append("Penalized: Contains experimental design dose specifications, not actual dosing data")
        
        # Penalty for dose mentions in other domain contexts
        other_domain_indicators = [
            r'(?i)body\s*weight.*\d+\.?\d*\s*g',  # Body weight context
            r'(?i)food\s*consumption.*\d+',  # Food consumption context  
            r'(?i)macroscopic.*examination',  # Macroscopic context
            r'(?i)clinical\s*observations.*\d+\s*mg/kg',  # Clinical observations mentioning dose
        ]
        
        other_domain_count = sum(1 for pattern in other_domain_indicators 
                                if re.search(pattern, content, re.IGNORECASE))
        
        if other_domain_count >= 1:
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: Dose mentions in non-exposure domain context")
        
        return confidence, evidence
    
    @staticmethod
    def validate_macroscopic_findings(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        """
        Validate MA (Macroscopic Findings) domain detection
        
        Args:
            content: Page content to validate
            initial_confidence: Initial confidence score
            evidence: List of evidence strings
            
        Returns:
            Tuple of (adjusted_confidence, updated_evidence)
        """
        confidence = initial_confidence
        
        # Check for actual macroscopic findings data
        actual_ma_indicators = [
            r'No\s*Visible\s*Lesions?',  # Common finding
            r'Animal\s+\d+.*lesion',  # Individual animal findings
            r'Enlarged.*organ',  # Organ enlargement findings
            r'Discoloration.*organ',  # Discoloration findings
            r'Macroscopic.*Examination',  # Examination results
            r'Gross.*Pathology',  # Gross pathology findings
            r'Necropsy.*findings?',  # Necropsy results
            r'Terminal.*necropsy',  # Terminal procedures
            r'Organ.*abnormal',  # Organ abnormalities
            r'Table.*Macroscopic',  # Macroscopic tables
            r'Liver.*enlarged',  # Specific organ findings
            r'Kidney.*discolored',  # Specific findings
            r'Heart.*abnormal',  # Cardiac findings
            r'Lung.*lesion',  # Pulmonary findings
            r'Brain.*hemorrhage',  # CNS findings
            r'Spleen.*enlarged',  # Splenic findings
            r'Mass.*detected',  # Mass/tumor findings
            r'Hemorrhage.*observed',  # Hemorrhage findings
            r'Pale.*appearance',  # Color changes
            r'Dark.*discoloration',  # Color changes
        ]
        
        actual_ma_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in actual_ma_indicators)
        
        # Heavy penalty if no actual macroscopic findings found
        if not actual_ma_found:
            confidence = max(0, confidence - 55)
            evidence.append("Penalized: No actual macroscopic findings data found")
        
        # Check for macroscopic examination tables (strong positive indicator)
        macro_table_indicators = [
            r'Table.*Macroscopic.*Observations?',
            r'Individual.*Macroscopic',
            r'Summary.*Macroscopic',
            r'Macroscopic.*Findings?.*Table',
            r'Gross.*Pathology.*Table',
            r'Necropsy.*Results?.*Table',
            r'Terminal.*Examination.*Table',
        ]
        
        table_found = any(re.search(pattern, content, re.IGNORECASE) 
                        for pattern in macro_table_indicators)
        
        if table_found:
            confidence += 30
            evidence.append("Bonus: Macroscopic examination table detected")
        
        # Check for specific organ findings (strong indicator)
        organ_findings = [
            r'(Liver|Kidney|Heart|Lung|Brain|Spleen|Stomach|Intestine).*\w+',
            r'LIVER.*\w+',
            r'KIDNEY.*\w+', 
            r'HEART.*\w+',
            r'LUNGS?.*\w+',
            r'BRAIN.*\w+',
            r'SPLEEN.*\w+',
            r'ADRENAL.*\w+',
            r'THYROID.*\w+',
            r'OVARIES.*\w+',
            r'TESTES.*\w+',
        ]
        
        organ_count = sum(1 for pattern in organ_findings 
                        if re.search(pattern, content, re.IGNORECASE))
        
        if organ_count >= 5:
            confidence += 25
            evidence.append(f"Bonus: Multiple organ findings detected ({organ_count})")
        elif organ_count >= 3:
            confidence += 15
            evidence.append(f"Bonus: Several organ findings detected ({organ_count})")
        elif organ_count >= 1:
            confidence += 10
            evidence.append(f"Bonus: Organ findings detected ({organ_count})")
        
        # Check for "No Visible Lesions" entries (very common in macro data)
        nvl_count = len(re.findall(r'No\s*Visible\s*Lesions?', content, re.IGNORECASE))
        if nvl_count >= 10:
            confidence += 30
            evidence.append(f"Bonus: Many 'No Visible Lesions' entries ({nvl_count})")
        elif nvl_count >= 5:
            confidence += 20
            evidence.append(f"Bonus: Multiple 'No Visible Lesions' entries ({nvl_count})")
        elif nvl_count >= 3:
            confidence += 10
            evidence.append(f"Bonus: 'No Visible Lesions' entries found ({nvl_count})")
        
        # Check for pathological terms (positive indicator)
        pathology_terms = [
            r'lesion',
            r'enlarged',
            r'discoloration',
            r'hemorrhage',
            r'necrosis',
            r'inflammation',
            r'congestion',
            r'edema',
            r'atrophy',
            r'hypertrophy',
            r'hyperplasia',
            r'fibrosis',
            r'mineralization',
            r'degeneration',
        ]
        
        path_count = sum(1 for term in pathology_terms 
                        if re.search(term, content, re.IGNORECASE))
        
        if path_count >= 5:
            confidence += 20
            evidence.append(f"Bonus: Multiple pathological terms detected ({path_count})")
        elif path_count >= 3:
            confidence += 15
            evidence.append(f"Bonus: Pathological terms detected ({path_count})")
        
        # Check for severity/grading (positive indicator)
        severity_indicators = [
            r'(Minimal|Slight|Moderate|Marked|Severe)',
            r'Grade\s*[1-5]',
            r'Score\s*[1-5]',
            r'Mild\s*to\s*moderate',
            r'Bilateral',
            r'Unilateral',
            r'Focal',
            r'Diffuse',
            r'Multifocal',
        ]
        
        severity_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in severity_indicators)
        
        if severity_found:
            confidence += 15
            evidence.append("Bonus: Severity/grading terms detected")
        
        # Protocol/methodology penalty
        methodology_indicators = [
            r'(?i)necropsy.*will.*be.*performed',
            r'(?i)macroscopic.*examination.*will',
            r'(?i)gross.*pathology.*procedure',
            r'(?i)terminal.*procedures?',
            r'(?i)animals?.*will.*be.*examined',
            r'(?i)pathology.*protocol',
            r'(?i)examination.*procedure',
            r'(?i)necropsy.*method',
        ]
        
        methodology_count = sum(1 for pattern in methodology_indicators 
                            if re.search(pattern, content, re.IGNORECASE))
        
        if methodology_count >= 1:
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: Appears to be macroscopic examination methodology/protocol text")
        
        # Administrative/summary penalty
        admin_indicators = [
            r'(?i)table\s+of\s+contents',
            r'(?i)objective.*macroscopic',
            r'(?i)study\s*design.*pathology',
            r'(?i)protocol.*pathology',
            r'(?i)methodology.*examination',
            r'(?i)summary.*pathology',
        ]
        
        admin_count = sum(1 for pattern in admin_indicators 
                        if re.search(pattern, content, re.IGNORECASE))
        
        if admin_count >= 1:
            confidence = max(0, confidence - 35)
            evidence.append("Penalized: Appears to be administrative text about pathology")
        
        # Check for animal death/removal reasons (relevant context)
        death_indicators = [
            r'Found\s*Dead',
            r'Killed\s*Terminal',
            r'Euthanized',
            r'Moribund',
            r'Scheduled\s*necropsy',
            r'Terminal\s*sacrifice',
            r'End\s*of\s*study',
        ]
        
        death_found = any(re.search(pattern, content, re.IGNORECASE) 
                        for pattern in death_indicators)
        
        if death_found:
            confidence += 10
            evidence.append("Bonus: Animal death/removal context detected")
        
        # Check for anatomical locations (positive indicator)
        anatomical_locations = [
            r'thoracic.*cavity',
            r'abdominal.*cavity',
            r'pelvic.*cavity',
            r'cranial.*cavity',
            r'peritoneal.*cavity',
            r'pleural.*cavity',
            r'mediastinum',
            r'mesentery',
            r'omentum',
        ]
        
        anatomical_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in anatomical_locations)
        
        if anatomical_found:
            confidence += 12
            evidence.append("Bonus: Anatomical location terms detected")
        
        # Penalty for just mentioning macroscopic without actual findings
        if re.search(r'(?i)macroscopic', content) and not actual_ma_found:
            confidence = max(0, confidence - 30)
            evidence.append("Penalized: Macroscopic mentioned but no actual findings found")
        
        return confidence, evidence
    
    @staticmethod
    def validate_trial_summary(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        """
        Enhanced TS (Trial Summary) domain validation
        """
        confidence = initial_confidence
        
        # Check for actual summary content vs protocol
        actual_ts_indicators = [
            r'(?i)(?:conclusion|summary).*(?:mtd|noael|findings?).*\d+\s*mg/kg',
            r'(?i)maximum\s+tolerated\s+dose.*(?:was|considered).*\d+\s*mg/kg',
            r'(?i)based\s+on\s+these\s+findings',
            r'(?i)test\s+article.*related.*(?:mortality|effects?)',
            r'(?i)no\s+test\s+article.*related\s+effects?',
            r'(?i)study.*(?:completed|conducted).*evaluate',
            r'(?i)results?.*showed?.*\d+\s*mg/kg',
        ]
        
        actual_ts_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in actual_ts_indicators)
        
        if not actual_ts_found:
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: No actual trial summary conclusions found")
        
        # Penalty for protocol/objective sections
        protocol_indicators = [
            r'(?i)objective.*this\s+study.*(?:were?|are)\s+to',
            r'(?i)proposed\s+study\s+schedule',
            r'(?i)experimental\s+design',
            r'(?i)protocol.*modification',
            r'(?i)draft\s+report.*\d{2}\s+\w{3}\s+\d{4}',  # Draft report dates
            r'(?i)test\s+facility.*attentive',
            r'(?i)sponsor.*pharmaceuticals?',
        ]
        
        protocol_count = sum(1 for pattern in protocol_indicators 
                            if re.search(pattern, content, re.IGNORECASE))
        
        if protocol_count >= 2:
            confidence = max(0, confidence - 60)
            evidence.append("Penalized: Appears to be protocol/objective text rather than summary")
        
        return confidence, evidence
    
    @staticmethod
    def validate_disposition(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        """
        Enhanced DS (Disposition) domain validation
        """
        confidence = initial_confidence
        
        # Check for actual disposition/mortality data
        actual_ds_indicators = [
            r'(?:Killed|Found)\s+(?:Terminal|Dead)',  # Specific disposition reasons
            r'Animal\s+\d+.*(?:Terminal|Dead|Euthanized)',  # Individual animal dispositions
            r'Group\s+\d+.*Day\s+\d+.*(?:Terminal|Dead)',  # Group disposition timing
            r'Removal\s+Reason.*(?:Term|FD)',  # Removal reason codes
            r'Table.*(?:Mortality|Disposition).*Data',  # Disposition tables
            r'\d{2}/\d{2}/\d{2}.*(?:\d{1,2}:\d{2}).*(?:Term|FD)',  # Dates with disposition codes
            r'Death.*Mode.*Day.*Week',  # Individual mortality table headers
        ]
        
        actual_ds_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in actual_ds_indicators)
        
        if not actual_ds_found:
            confidence = max(0, confidence - 55)
            evidence.append("Penalized: No actual disposition/mortality data found")
        
        # Check for disposition methodology (penalty)
        methodology_indicators = [
            r'(?i)animals?\s+(?:will\s+be|to\s+be)\s+euthanized',
            r'(?i)moribund\s+animals?\s+will\s+be',
            r'(?i)method\s+of\s+euthanasia',
            r'(?i)terminal\s+procedures?',
            r'(?i)animals?\s+found\s+dead\s+will\s+be',
            r'(?i)co2?\s+inhalation.*exsanguination',
        ]
        
        methodology_count = sum(1 for pattern in methodology_indicators 
                            if re.search(pattern, content, re.IGNORECASE))
        
        if methodology_count >= 1:
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: Appears to be disposition methodology/protocol text")
        
        return confidence, evidence
    
    @staticmethod
    def validate_food_water(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        """
        Enhanced FW (Food and Water Consumption) domain validation
        """
        confidence = initial_confidence
        
        # Check for actual consumption DATA tables
        actual_fw_indicators = [
            r'Table\s+\d+:.*Food\s*Consumption.*Data',  # Specific FW table titles
            r'Individual.*Food\s*Consumption.*Data',  # Individual consumption tables
            r'Summary.*Food\s*Consumption.*Data',  # Summary consumption tables
            r'Daily\s*Food\s*Cons.*Per\s*Animal.*\(g\)',  # Actual consumption measurements
            r'Animal.*\d+→\d+.*\d+→\d+',  # Daily consumption intervals
            r'Cage.*Mean.*\d+.*SD.*\d+',  # Consumption statistics
            r'\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+.*g',  # Multiple consumption values
        ]
        
        actual_fw_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in actual_fw_indicators)
        
        if not actual_fw_found:
            confidence = max(0, confidence - 60)
            evidence.append("Penalized: No actual food consumption data tables found")
        
        # Penalty for protocol food specifications
        protocol_food_indicators = [
            r'(?i)certified\s+laboratory\s+diet',
            r'(?i)food\s*will\s*be\s*weighed\s*and\s*recorded',
            r'(?i)diet.*offered\s+ad\s+libitum',
            r'(?i)water.*available\s+ad\s+libitum',
            r'(?i)food\s*consumption.*will\s*be\s*collected',
            r'(?i)diet.*analyzed\s*for\s*contaminants',
        ]
        
        protocol_count = sum(1 for pattern in protocol_food_indicators 
                            if re.search(pattern, content, re.IGNORECASE))
        
        if protocol_count >= 1:
            confidence = max(0, confidence - 55)
            evidence.append("Penalized: Contains protocol food specifications, not actual data")
        
        return confidence, evidence
    
    @staticmethod
    def validate_trial_arms(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        """
        Enhanced TA (Trial Arms) domain validation
        """
        confidence = initial_confidence
        
        # Check for actual treatment group assignment data
        actual_ta_indicators = [
            r'Group\s+\d+.*\d+\s*mg/kg.*\d+\s*(?:Males?|Females?)',  # Complete group assignments
            r'Treatment.*Group.*Dose.*Animals?',  # Treatment group tables
            r'Randomization.*Group.*Assignment',  # Randomization tables
            r'Animal\s+\d+.*Group\s+\d+.*\d+\s*mg/kg',  # Individual assignments
            r'Table.*Group.*Assignment',  # Group assignment tables
            r'Dose\s+Level.*Number\s+of\s+Animals?',  # Dose level tables
        ]
        
        actual_ta_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in actual_ta_indicators)
        
        if not actual_ta_found:
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: No actual trial arm assignment data found")
        
        # Check for experimental design methodology (penalty)
        methodology_indicators = [
            r'(?i)experimental\s+design',
            r'(?i)justification\s+of\s+dose',
            r'(?i)males?\s+and\s+females?\s+were\s+chosen',
            r'(?i)total\s+number\s+of\s+animals?.*minimum\s+required',
            r'(?i)study.*designed.*accomplish.*objectives?',
            r'(?i)route\s+of\s+administration.*intravenous',
        ]
        
        methodology_count = sum(1 for pattern in methodology_indicators 
                            if re.search(pattern, content, re.IGNORECASE))
        
        if methodology_count >= 2:
            confidence = max(0, confidence - 55)
            evidence.append("Penalized: Appears to be experimental design methodology")
        
        return confidence, evidence
    
    @staticmethod
    def validate_comments(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        confidence = initial_confidence
        
        # Check for actual comments/annotations
        actual_co_indicators = [
            r'Comment.*\w+',  # Comment fields
            r'Note.*\w+',  # Notes
            r'Deviation.*\w+',  # Protocol deviations
            r'Amendment.*\w+',  # Amendments
            r'Remark.*\w+',  # Remarks
            r'Observation.*comment',  # Observation comments
            r'RC:.*',  # Result comments (common notation)
            r'\*.*comment',  # Asterisk comments
            r'See.*note',  # Reference to notes
            r'Corrected.*weight',  # Correction comments
            r'Protocol.*change',  # Protocol changes
        ]
        
        if not any(re.search(pattern, content, re.IGNORECASE) for pattern in actual_co_indicators):
            confidence = max(0, confidence - 40)
            evidence.append("Penalized: No actual comments/annotations found")
        
        # Check for comment tables or sections
        if re.search(r'Comment.*Information|Table.*Comment', content, re.IGNORECASE):
            confidence += 25
            evidence.append("Bonus: Comment table/section detected")
        
        # Check for deviation documentation
        if re.search(r'deviation.*documented|protocol.*deviation', content, re.IGNORECASE):
            confidence += 15
            evidence.append("Bonus: Protocol deviation documentation found")
        
        return confidence, evidence
    
    @staticmethod
    def validate_laboratory(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        confidence = initial_confidence
        
        # Check for actual lab data with more specific patterns
        actual_lb_indicators = [
            r'\d+\.?\d*\s*(mg/dL|mmol/L|U/L|IU/L|g/dL)',  # Lab values with units
            r'(ALT|AST|BUN|Creatinine|Glucose).*:\s*\d+',  # Lab parameters with values
            r'Hematology.*Results?.*\d+',  # Hematology results
            r'Clinical\s*Chemistry.*Results?.*\d+',  # Clinical chemistry results
            r'WBC.*:\s*\d+',  # White blood cells with values
            r'RBC.*:\s*\d+',  # Red blood cells with values
            r'Hemoglobin.*:\s*\d+\.?\d*',  # Hemoglobin with values
            r'Platelet.*count.*:\s*\d+',  # Platelet counts with values
            r'Table\s+\d+:.*Laboratory.*Results?',  # Numbered lab tables
            r'Table\s+\d+:.*Clinical\s*Chemistry',  # Clinical chemistry tables
            r'Table\s+\d+:.*Hematology',  # Hematology tables
            r'Animal\s+\d+.*\d+\.?\d*\s*(mg/dL|U/L)',  # Individual animal lab values
            r'Group\s+\d+.*Mean.*\d+\.?\d*\s*(mg/dL|U/L)',  # Group lab summaries
        ]
        
        actual_lb_found = any(re.search(pattern, content, re.IGNORECASE) 
                            for pattern in actual_lb_indicators)
        
        # Heavy penalty if no actual lab data found
        if not actual_lb_found:
            confidence = max(0, confidence - 55)
            evidence.append("Penalized: No actual laboratory data found")
        
        # Check for lab data tables (strong positive indicator)
        lab_table_indicators = [
            r'Individual.*Laboratory.*Results?',
            r'Summary.*Clinical\s*Chemistry',
            r'Summary.*Hematology',
            r'Laboratory.*Data.*Table',
            r'Clinical\s*Pathology.*Results?',
        ]
        
        table_found = any(re.search(pattern, content, re.IGNORECASE) 
                        for pattern in lab_table_indicators)
        
        if table_found:
            confidence += 30
            evidence.append("Bonus: Laboratory data table detected")
        
        # Protocol/methodology penalty (this is the key addition)
        methodology_indicators = [
            r'(?i)laboratory.*will.*be.*analyzed',
            r'(?i)blood.*samples?.*will.*be.*collected',
            r'(?i)clinical\s*pathology.*will.*be.*performed',
            r'(?i)hematology.*will.*be.*evaluated',
            r'(?i)serum.*chemistry.*will.*be.*analyzed',
            r'(?i)protocol.*laboratory',
            r'(?i)laboratory.*procedure',
            r'(?i)blood.*collection.*procedure',
            r'(?i)clinical\s*pathology.*procedure',
            r'(?i)animals?.*will.*be.*bled',
            r'(?i)samples?.*will.*be.*analyzed',
            r'(?i)laboratory.*analysis.*will',
        ]
        
        methodology_count = sum(1 for pattern in methodology_indicators 
                            if re.search(pattern, content, re.IGNORECASE))
        
        if methodology_count >= 1:
            confidence = max(0, confidence - 60)
            evidence.append("Penalized: Appears to be laboratory methodology/protocol text")
        
        # Administrative/summary penalty
        admin_indicators = [
            r'(?i)table\s+of\s+contents',
            r'(?i)protocol.*section',
            r'(?i)study\s*design.*laboratory',
            r'(?i)objective.*laboratory',
            r'(?i)test\s*facility.*laboratory',
            r'(?i)laboratory.*sop',
            r'(?i)standard\s*operating\s*procedure',
        ]
        
        admin_count = sum(1 for pattern in admin_indicators 
                        if re.search(pattern, content, re.IGNORECASE))
        
        if admin_count >= 1:
            confidence = max(0, confidence - 40)
            evidence.append("Penalized: Appears to be administrative/protocol text about laboratory")
        
        # Check for multiple lab parameters (only if actual data found)
        if actual_lb_found:
            lab_params = re.findall(r'(ALT|AST|BUN|Creatinine|Glucose|WBC|RBC|Hemoglobin)', content, re.IGNORECASE)
            if len(lab_params) >= 5:
                confidence += 25
                evidence.append(f"Bonus: Multiple lab parameters detected ({len(lab_params)})")
            elif len(lab_params) >= 3:
                confidence += 15
                evidence.append(f"Bonus: Several lab parameters detected ({len(lab_params)})")
        
        # Penalty for just mentioning laboratory without actual data
        if re.search(r'(?i)laboratory|clinical\s*chemistry|hematology', content) and not actual_lb_found:
            confidence = max(0, confidence - 35)
            evidence.append("Penalized: Laboratory mentioned but no actual data found")
        
        return confidence, evidence
    
    @staticmethod
    def validate_pharmacokinetics(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        confidence = initial_confidence
        
        # Check for actual PK data
        actual_pc_indicators = [
            r'C(max|min).*\d+',  # Cmax, Cmin values
            r'T(max|half).*\d+',  # Tmax, Thalf values
            r'AUC.*\d+',  # Area under curve
            r'Clearance.*\d+',  # Clearance values
            r'Volume.*distribution.*\d+',  # Volume of distribution
            r'Concentration.*\d+\.?\d*\s*(ng/mL|μg/mL)',  # Concentration values
            r'Plasma.*level.*\d+',  # Plasma levels
            r'Bioavailability.*\d+',  # Bioavailability
            r'Half.*life.*\d+',  # Half-life
            r'PK.*parameter',  # PK parameters
        ]
        
        if not any(re.search(pattern, content, re.IGNORECASE) for pattern in actual_pc_indicators):
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: No actual pharmacokinetic data found")
        
        return confidence, evidence
    
    @staticmethod
    def validate_microscopic(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        confidence = initial_confidence
        
        # Check for actual microscopic findings
        actual_mi_indicators = [
            r'Microscopic.*examination',  # Microscopic exam
            r'Histopathology.*\w+',  # Histopathology findings
            r'Section.*\w+.*cell',  # Tissue sections
            r'(Inflammation|Necrosis|Fibrosis|Hyperplasia).*Grade\s*\d+',  # Graded findings
            r'H&E.*stain',  # Staining methods
            r'Tissue.*section',  # Tissue sections
            r'Cell.*infiltration',  # Cellular findings
            r'Degenerative.*changes',  # Pathological changes
            r'Vacuolation.*hepatocyte',  # Specific cellular findings
            r'Portal.*inflammation',  # Anatomical findings
        ]
        
        if not any(re.search(pattern, content, re.IGNORECASE) for pattern in actual_mi_indicators):
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: No actual microscopic findings found")
        
        return confidence, evidence
    
    @staticmethod
    def validate_organ_measurements(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        confidence = initial_confidence
        
        # Check for actual organ weight/measurement data
        actual_om_indicators = [
            r'(Liver|Heart|Kidney|Brain|Spleen).*\d+\.?\d*\s*g',  # Organ weights
            r'Organ.*weight.*\d+',  # Organ weight data
            r'Absolute.*weight.*\d+',  # Absolute weights
            r'Relative.*weight.*\d+',  # Relative weights
            r'Body.*weight.*ratio',  # Body weight ratios
            r'Terminal.*weight.*\d+',  # Terminal weights
            r'Necropsy.*weight',  # Necropsy weights
            r'Table.*Organ.*Weight',  # Organ weight tables
        ]
        
        if not any(re.search(pattern, content, re.IGNORECASE) for pattern in actual_om_indicators):
            confidence = max(0, confidence - 50)
            evidence.append("Penalized: No actual organ measurement data found")
        
        return confidence, evidence
    
    @staticmethod
    def validate_pharmacology(content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
        confidence = initial_confidence
        
        # Check for pharmacology endpoint data
        actual_pp_indicators = [
            r'(IC50|EC50|ED50).*\d+',  # Dose-response parameters
            r'Efficacy.*\d+',  # Efficacy measurements
            r'Response.*\d+.*%',  # Response percentages
            r'Inhibition.*\d+.*%',  # Inhibition percentages
            r'Activity.*\d+',  # Activity measurements
            r'Potency.*\d+',  # Potency data
            r'Selectivity.*\d+',  # Selectivity data
            r'Binding.*affinity.*\d+',  # Binding affinity
        ]
        
        if not any(re.search(pattern, content, re.IGNORECASE) for pattern in actual_pp_indicators):
            confidence = max(0, confidence - 45)
            evidence.append("Penalized: No actual pharmacology parameter data found")
        
        return confidence, evidence

def validate_domain_content(domain_code: str, content: str, initial_confidence: float, evidence: List[str]) -> Tuple[float, List[str]]:
    """
    Main validation function that routes to appropriate domain validator
    
    Args:
        domain_code: SEND domain code (VS, CL, DM, EX, etc.)
        content: Page content to validate
        initial_confidence: Initial confidence score
        evidence: List of evidence strings
        
    Returns:
        Tuple of (adjusted_confidence, updated_evidence)
    """
    validator = DomainValidator()
    
    if domain_code == 'VS':
        return validator.validate_vital_signs(content, initial_confidence, evidence)
    elif domain_code == 'CL':
        return validator.validate_clinical_observations(content, initial_confidence, evidence)
    elif domain_code == 'FW':
        return validator.validate_food_water(content, initial_confidence, evidence)
    elif domain_code == 'DM':
        return validator.validate_demographics(content, initial_confidence, evidence)
    elif domain_code == 'EX':
        return validator.validate_exposure(content, initial_confidence, evidence)
    elif domain_code == 'BW':
        return validator.validate_body_weight(content, initial_confidence, evidence)
    elif domain_code == 'MA':
        return validator.validate_macroscopic_findings(content, initial_confidence, evidence)
    elif domain_code == 'TS':
        return validator.validate_trial_summary(content, initial_confidence, evidence)
    elif domain_code == 'DS':
        return validator.validate_disposition(content, initial_confidence, evidence)
    elif domain_code == 'TA':
        return validator.validate_trial_arms(content, initial_confidence, evidence)
    elif domain_code == 'CO':
        return validator.validate_comments(content, initial_confidence, evidence)
    elif domain_code == 'LB':
        return validator.validate_laboratory(content, initial_confidence, evidence)
    elif domain_code == 'PC':
        return validator.validate_pharmacokinetics(content, initial_confidence, evidence)
    elif domain_code == 'MI':
        return validator.validate_microscopic(content, initial_confidence, evidence)
    elif domain_code == 'OM':
        return validator.validate_organ_measurements(content, initial_confidence, evidence)
    elif domain_code == 'PP':
        return validator.validate_pharmacology(content, initial_confidence, evidence)
    else:
        # No specific validation for this domain
        return initial_confidence, evidence


# Convenience function for common validation patterns
def has_actual_data_tables(content: str) -> bool:
    """Check if content contains actual data tables vs methodology"""
    data_table_patterns = [
        r'Table\s+\d+:',  # Numbered tables
        r'\d+\s+\d+\s+\d+',  # Multiple numbers in rows
        r'Animal\s+\d+.*\d+',  # Animal data rows
        r'Subject\s+\d+.*\d+',  # Subject data rows
    ]
    
    return any(re.search(pattern, content, re.IGNORECASE) 
               for pattern in data_table_patterns)


def is_methodology_content(content: str) -> bool:
    """Check if content appears to be methodology/protocol text"""
    methodology_patterns = [
        r'(?i)will\s+be\s+(observed|measured|recorded)',
        r'(?i)protocol\s+(section|amendment)',
        r'(?i)study\s+design',
        r'(?i)methodology',
        r'(?i)procedures?\s+will',
        r'(?i)objective',
        r'(?i)at\s+minimum',
    ]
    
    return any(re.search(pattern, content, re.IGNORECASE) 
               for pattern in methodology_patterns)