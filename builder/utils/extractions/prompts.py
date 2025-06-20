# extraction/prompts.py
from typing import Dict, List
from builder.utils.send_utils import get_domain_description, get_column_description, get_required_columns

class ExtractionPrompts:
    """Centralized prompt management for domain extraction"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Base system prompt for all extractions"""
        return """You are an expert toxicology data analyst specializing in SEND (Standard for Exchange of Nonclinical Data) format extraction from study PDFs.

                Your task is to extract structured data from toxicology study documents and format it according to SEND guidelines.

                Key principles:
                1. Extract only factual data present in the text
                2. Follow SEND column naming conventions exactly
                3. Ensure data consistency across records
                4. Use appropriate controlled terminology
                5. Handle missing data gracefully
                6. Maintain referential integrity between domains

                Always return data in valid CSV format with proper headers."""

    @staticmethod
    def get_domain_extraction_prompt(domain: str, text: str, chunk_info: Dict = None) -> str:
        """Generate domain-specific extraction prompt"""
        
        domain_desc = get_domain_description(domain)
        required_cols = get_required_columns(domain)
        
        # Create a quick reference for key columns
        key_columns_info = []
        for col in required_cols[:5]:  # Show first 5 key columns
            desc = get_column_description(domain, col)
            key_columns_info.append(f"{col} ({desc})")
        
        chunk_context = ""
        if chunk_info:
            chunk_context = f"""
                CHUNK INFORMATION:
                - Processing chunk {chunk_info.get('current', 1)} of {chunk_info.get('total', 1)}
                - This is a partial view of the document
                - Maintain consistent formatting for data combination
                """

        # Create the required columns string for explicit requirements
        required_cols_str = ", ".join(required_cols)

        base_prompt = f"""
        DOMAIN: {domain} ({domain_desc})

        KEY COLUMNS TO EXTRACT:
        {chr(10).join(key_columns_info)}

        {chunk_context}

        CRITICAL REQUIREMENTS:
        - The output CSV MUST include ALL of these required columns: {required_cols_str}
        - If any required column data is not found in the content, include the column with empty values
        - For {domain} domain, ensure all required columns are present in the header row
        - Do not skip any required columns - they must all appear in the CSV output

        MANDATORY CSV HEADER:
        {required_cols_str}

        INSTRUCTIONS:
        1. Analyze the provided text for {domain} domain data
        2. USUBJID should be formatted as STUDYID-SUBJID and be globally unique
        3. Extract all relevant data points according to column descriptions
        4. Format as CSV with appropriate SEND columns starting with the exact header above
        5. Include required columns: STUDYID, DOMAIN, USUBJID
        6. Ensure sequence numbers are unique per subject
        7. Use ISO date format (YYYY-MM-DD) where applicable
        8. Follow controlled terminology where specified
        9. IMPORTANT: Your CSV must start with exactly this header: {required_cols_str}

        TEXT TO ANALYZE:
        {text}

        Return only the CSV data with the mandatory header row first, followed by data rows. No explanations.
        """
        
        # Add domain-specific instructions with column descriptions
        domain_instructions = ExtractionPrompts._get_domain_specific_instructions(domain)
        if domain_instructions:
            base_prompt += f"\n\nDOMAIN-SPECIFIC REQUIREMENTS:\n{domain_instructions}"
        
        return base_prompt
    
    @staticmethod
    def _get_domain_specific_instructions(domain: str) -> str:
        """Get domain-specific extraction instructions with column descriptions"""
        
        # Get required columns for the domain
        required_cols = get_required_columns(domain)
        
        # Build column descriptions
        column_descriptions = []
        for col in required_cols:
            description = get_column_description(domain, col)
            column_descriptions.append(f"- {col}: {description}")
        
        # Create the instruction text
        column_text = "\n".join(column_descriptions)
        
        instructions = {
                'CL': f"""
            Clinical Observations Domain (CL):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Look for animal observations like activity, salivation, breathing patterns, behavioral changes
            - CLTESTCD: Use standardized codes (CLACTIV for activity, CLSALIV for salivation, CLRESP for respiration)
            - CLSEV: Use controlled terminology (MINIMAL, MILD, MODERATE, MARKED, SEVERE)
            - CLCAT: Default to "GENERAL OBSERVATIONS" if category not specified
            - CLLOC: Default to "WHOLE BODY" if location not specified
            - CLSTRESC: Standardize results to NORMAL/ABNORMAL when possible
            """,
                'BW': f"""
            Body Weight Domain (BW):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - BWTESTCD: Always use "BW" for body weight measurements
            - BWTEST: Always use "Body Weight"
            - BWORRESU: Typically "g" (grams) or "kg" (kilograms)
            - Extract all weight measurements with their corresponding study days
            - Ensure BWORRES contains numeric values only
            """,
                'DM': f"""
            Demographics Domain (DM):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - SPECIES: Use controlled terminology (RAT, MOUSE, DOG, etc.)
            - SEX: Use M for Male, F for Female
            - Extract animal IDs, group assignments, and baseline characteristics
            - ARMCD: Use group codes like G1, G2, G3, CONTROL
            - ARM: Use descriptive group names (Control, Low Dose, High Dose)
            - RFSTDTC: Use study start date in YYYY-MM-DD format
            """,
                'DS': f"""
            Disposition Domain (DS):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract subject completion and discontinuation information
            - DSDECOD: Use controlled terminology (SCHEDULED SACRIFICE, FOUND DEAD, MORIBUND SACRIFICE, EUTHANIZED)
            - DSTERM: Extract the reported disposition term as written
            - DSSTDTC: Use study termination date in YYYY-MM-DD format
            - Include all animals and their final disposition status
            """,
                'TS': f"""
            Trial Summary Domain (TS):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract study design characteristics and trial attributes
            - TSPARMCD: Use standard parameter codes (TITLE, SPONSOR, PHASE, etc.)
            - TSPARM: Use descriptive parameter names
            - TSVAL: Extract parameter values as reported in study
            - Include study title, sponsor, species, duration, and other trial characteristics
            """,
                'TA': f"""
            Trial Arms Domain (TA):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract planned treatment arms for the study
            - ARMCD: Use group codes (G1, G2, CONTROL, etc.)
            - ARM: Use descriptive arm names (Vehicle Control, Low Dose, High Dose)
            - ETCD: Use element codes for study elements
            - ELEMENT: Describe study elements (Treatment, Recovery, etc.)
            - TAETORD: Sequence of elements within each arm
            """,
                'TE': f"""
            Trial Elements Domain (TE):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract planned study elements and their relationships
            - ETCD: Use element codes (TREAT, RECOV, DOSING, etc.)
            - ELEMENT: Describe each study element
            - TESTRL: Define relationships between elements
            - Map out the overall study design structure
            """,
                'TX': f"""
            Trial Sets Domain (TX):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract additional trial design information
            - TXPARMCD: Use parameter codes for trial sets
            - TXPARM: Use descriptive parameter names
            - TXVAL: Extract parameter values
            - Include study design details not captured in other domains
            """,
                'PP': f"""
            Planned Protocols Domain (PP):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract planned protocol procedures and timepoints
            - PPTESTCD: Use test codes for planned procedures
            - PPTEST: Use descriptive test names
            - Include planned clinical observations, sample collections, and measurements
            - Map procedures to study timepoints
            """,
                'SE': f"""
            Subject Elements Domain (SE):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract subject-specific study elements and timing
            - ETCD: Use element codes matching TE domain
            - ELEMENT: Use element descriptions matching TE domain
            - SESTDTC: Use actual start dates for elements in YYYY-MM-DD format
            - SEENDTC: Use actual end dates for elements in YYYY-MM-DD format
            - Track actual vs planned study conduct for each subject
            """,
                'EX': f"""
            Exposure Domain (EX):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - EXTRT: Extract treatment names (Test Article, Vehicle Control, etc.)
            - EXROUTE: Use controlled terminology (ORAL, IV, SC, IM, DERMAL, etc.)
            - EXDOSE: Extract numeric dose values
            - EXDOSU: Include dose units (mg/kg, mg/kg/day, etc.)
            - EXDOSFRQ: Use standard frequency codes (QD, BID, TID, etc.)
            - Extract dosing schedules for each treatment group
            """,
                'PC': f"""
            Pharmacokinetic Concentrations Domain (PC):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract drug concentration measurements from PK studies
            - PCTESTCD: Use parameter codes (PARENT, METAB1, etc.)
            - PCTEST: Use descriptive test names for analytes
            - PCORRES: Extract concentration values as reported
            - PCORRESU: Include original units (ng/mL, μg/mL, etc.)
            - PCSPEC: Use specimen types (PLASMA, SERUM, BLOOD)
            - PCDTC: Use collection date/time in YYYY-MM-DDTHH:MM format
            """,
                'LB': f"""
            Laboratory Test Results Domain (LB):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - LBSPEC: Use controlled terminology (SERUM, PLASMA, BLOOD, URINE)
            - LBTESTCD: Use standard lab test codes (ALT, AST, GLUC, CREAT, HGB, etc.)
            - LBBLFL: Use 'Y' for baseline measurements, 'N' for others
            - LBORRES: Extract original result values as reported
            - LBORRESU: Include original units (mg/dL, U/L, g/dL, etc.)
            - Extract all clinical pathology parameters with their values and units
            """,
                'MA': f"""
            Macroscopic Findings Domain (MA):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract gross pathology findings from necropsy reports
            - MALOC: Use specific organ/tissue locations (LIVER, LUNG, HEART, etc.)
            - MASTRESC: Use NORMAL for "No Visible Lesions" or ABNORMAL for findings
            - MAORRES: Extract original pathologist descriptions
            - Include both normal and abnormal findings for completeness
            """,
                'MI': f"""
            Microscopic Findings Domain (MI):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract histopathology findings from microscopic examination
            - MITESTCD: Use test codes for microscopic examinations
            - MITEST: Use descriptive test names for histopathology
            - MIORRES: Extract original pathologist findings as reported
            - MISTRESC: Standardize to NORMAL/ABNORMAL when possible
            - MILOC: Use specific organ/tissue locations
            - MISEV: Use severity scale (MINIMAL, MILD, MODERATE, MARKED, SEVERE)
            - Include both normal and abnormal microscopic findings
            """,
                'OM': f"""
            Organ Measurements Domain (OM):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract organ weight and measurement data
            - OMTESTCD: Use test codes for organ measurements (ORGWGT, LENGTH, etc.)
            - OMTEST: Use descriptive names (Organ Weight, Length, etc.)
            - OMORRES: Extract measurement values as reported
            - OMORRESU: Include original units (g, mg, cm, mm, etc.)
            - OMLOC: Use specific organ names (LIVER, HEART, KIDNEY, etc.)
            - Extract both absolute and relative organ weights when available
            """,
                'PA': f"""
            Palpable Masses Domain (PA):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract palpable mass findings from physical examinations
            - PATESTCD: Use test codes for palpable mass examinations
            - PATEST: Use descriptive test names
            - PAORRES: Extract mass descriptions as reported
            - PASTRESC: Standardize to NORMAL/ABNORMAL when possible
            - PALOC: Use specific anatomical locations
            - Include size, consistency, and other mass characteristics
            """,
                'PM': f"""
            Physical Measurements Domain (PM):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract physical measurements other than body weight
            - PMTESTCD: Use test codes (LENGTH, HEIGHT, CIRCUM, etc.)
            - PMTEST: Use descriptive measurement names
            - PMORRES: Extract measurement values as reported
            - PMORRESU: Include original units (cm, mm, inches, etc.)
            - Extract growth measurements, body dimensions, and other physical parameters
            """,
                'EG': f"""
            ECG Test Results Domain (EG):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract electrocardiogram test results
            - EGTESTCD: Use standard ECG parameter codes (HR, PR, QRS, QT, etc.)
            - EGTEST: Use descriptive parameter names (Heart Rate, PR Interval, etc.)
            - EGORRES: Extract ECG values as reported
            - EGORRESU: Include original units (bpm, msec, mV, etc.)
            - EGBLFL: Use 'Y' for baseline ECGs, 'N' for others
            - Extract all ECG parameters and measurements
            """,
                'CV': f"""
            Cardiovascular Test Results Domain (CV):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract cardiovascular test results beyond ECG
            - CVTESTCD: Use test codes for CV parameters (SYSBP, DIABP, etc.)
            - CVTEST: Use descriptive test names (Systolic BP, Diastolic BP, etc.)
            - CVORRES: Extract CV values as reported
            - CVORRESU: Include original units (mmHg, bpm, etc.)
            - CVBLFL: Use 'Y' for baseline measurements, 'N' for others
            - Extract blood pressure, heart rate, and other cardiovascular parameters
            """,
                'VS': f"""
            Vital Signs Domain (VS):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract vital signs measurements
            - VSTESTCD: Use standard vital signs codes (TEMP, RESP, etc.)
            - VSTEST: Use descriptive test names (Temperature, Respiration Rate, etc.)
            - VSORRES: Extract vital sign values as reported
            - VSORRESU: Include original units (°C, °F, /min, etc.)
            - VSBLFL: Use 'Y' for baseline measurements, 'N' for others
            - Extract temperature, respiration rate, and other vital signs
            """,
                'DD': f"""
            Death Diagnosis Domain (DD):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract cause of death information
            - DDTESTCD: Use test codes for death diagnosis
            - DDTEST: Use descriptive test names
            - DDORRES: Extract cause of death as reported
            - DDSTRESC: Standardize death causes when possible
            - Extract pathologist's determination of cause of death
            - Include both immediate and contributing causes
            """,
                'FW': f"""
            Food and Water Consumption Domain (FW):
            Required columns and their meanings:
            {column_text}

            Extraction Guidelines:
            - Extract food and water consumption measurements
            - FWTESTCD: Use test codes (FOODCONS, WATERCONS, etc.)
            - FWTEST: Use descriptive names (Food Consumption, Water Consumption)
            - FWORRES: Extract consumption values as reported
            - FWORRESU: Include original units (g, mL, g/day, mL/day, etc.)
            - Extract both individual and group consumption data
            - Include consumption per animal and per cage when available
            """
        }
        
        return instructions.get(domain, f"""
            {domain} Domain:
            Required columns and their meanings:
            {column_text}

            Extract data according to SEND {domain} domain requirements using the column descriptions above.
            """)
    @staticmethod
    def get_validation_prompt(domain: str, extracted_data: str) -> str:
        """Generate validation prompt for extracted data"""
        return f"""
            Validate the following {domain} domain data for SEND compliance:

            DATA:
            {extracted_data}

            Check for:
            1. Required columns are present
            2. STUDYID and DOMAIN values are consistent
            3. USUBJID format is correct (STUDYID-SUBJID)
            4. Sequence numbers are unique per subject
            5. Date formats are ISO compliant (YYYY-MM-DD)
            6. Controlled terminology is used correctly
            7. No duplicate records

            Return:
            - "VALID" if data passes all checks
            - List of specific issues if validation fails
            """

    @staticmethod
    def get_chunk_combination_prompt(domain: str, chunk_results: List[str]) -> str:
        """Generate prompt for combining chunk results"""
        combined_data = "\n".join(chunk_results)
        
        return f"""
            Combine and normalize the following {domain} domain data chunks:

            {combined_data}

            Tasks:
            1. Remove duplicate headers
            2. Ensure consistent column structure
            3. Normalize sequence numbers within each USUBJID
            4. Remove any duplicate records
            5. Sort by USUBJID and sequence number

            Return the final consolidated CSV data."""