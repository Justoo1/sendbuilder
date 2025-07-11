# builder/management/commands/fix_studyid_usubjid.py
# Create this file to fix existing data

import re
import pandas as pd
from io import StringIO
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from builder.models import Study, ExtractedDomain
from builder.utils.extractions.send_validator import post_process_domain_data
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix STUDYID and USUBJID format issues in existing extracted domains'

    def add_arguments(self, parser):
        parser.add_argument(
            '--study-id',
            type=int,
            help='Fix only specific study ID (optional)',
        )
        parser.add_argument(
            '--domain',
            type=str,
            help='Fix only specific domain (optional)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force fix even if data looks correct',
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting STUDYID/USUBJID format fix...")
        
        # Get query filters
        filters = {}
        if options['study_id']:
            filters['study_id'] = options['study_id']
        if options['domain']:
            filters['domain__code'] = options['domain']
        
        # Get extracted domains to fix
        extracted_domains = ExtractedDomain.objects.filter(**filters).select_related('study', 'domain')
        
        if not extracted_domains.exists():
            self.stdout.write(self.style.WARNING("No extracted domains found matching criteria"))
            return
        
        self.stdout.write(f"Found {extracted_domains.count()} extracted domains to check")
        
        fixed_count = 0
        error_count = 0
        
        for extracted_domain in extracted_domains:
            try:
                result = self.fix_extracted_domain(extracted_domain, options['dry_run'], options['force'])
                if result['fixed']:
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Fixed {extracted_domain.study.study_number}-{extracted_domain.domain.code}: {result['message']}")
                    )
                elif result['checked']:
                    self.stdout.write(
                        self.style.WARNING(f"○ {extracted_domain.study.study_number}-{extracted_domain.domain.code}: {result['message']}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ {extracted_domain.study.study_number}-{extracted_domain.domain.code}: {result['message']}")
                    )
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"✗ Error processing {extracted_domain.study.study_number}-{extracted_domain.domain.code}: {e}")
                )
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"SUMMARY:")
        self.stdout.write(f"  Total domains checked: {extracted_domains.count()}")
        self.stdout.write(f"  Domains fixed: {fixed_count}")
        self.stdout.write(f"  Errors: {error_count}")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes were made"))
        elif fixed_count > 0:
            self.stdout.write(self.style.SUCCESS("Fix completed successfully!"))

    def fix_extracted_domain(self, extracted_domain, dry_run=False, force=False):
        """Fix a single extracted domain"""
        study = extracted_domain.study
        domain_code = extracted_domain.domain.code
        
        # Get the current data
        content = extracted_domain.content
        if not content:
            return {'fixed': False, 'checked': False, 'message': 'No content to fix'}
        
        # Convert to DataFrame
        try:
            df = pd.DataFrame(content)
        except Exception as e:
            return {'fixed': False, 'checked': False, 'message': f'Could not convert to DataFrame: {e}'}
        
        if df.empty:
            return {'fixed': False, 'checked': False, 'message': 'Empty DataFrame'}
        
        # Check if fix is needed
        issues_found = self.analyze_issues(df, study, domain_code)
        
        if not issues_found['has_issues'] and not force:
            return {'fixed': False, 'checked': True, 'message': 'No issues found'}
        
        if dry_run:
            return {
                'fixed': False, 
                'checked': True, 
                'message': f'Would fix: {", ".join(issues_found["issues"])}'
            }
        
        # Apply the fix
        try:
            with transaction.atomic():
                # Re-process the data with study context
                fixed_df = post_process_domain_data(df, domain_code, study)
                
                # Update the extracted domain
                extracted_domain.content = fixed_df.to_dict('records')
                extracted_domain.save()
                
                # Regenerate XPT file if needed
                if extracted_domain.xpt_file:
                    try:
                        xpt_content = self.regenerate_xpt_file(fixed_df, domain_code)
                        if xpt_content:
                            from django.core.files.base import ContentFile
                            xpt_file = ContentFile(xpt_content, name=f"{domain_code}.xpt")
                            extracted_domain.xpt_file.save(f"{domain_code}.xpt", xpt_file, save=True)
                    except Exception as e:
                        logger.warning(f"Could not regenerate XPT file: {e}")
                
                return {
                    'fixed': True, 
                    'checked': True, 
                    'message': f'Fixed {len(fixed_df)} records: {", ".join(issues_found["issues"])}'
                }
                
        except Exception as e:
            return {'fixed': False, 'checked': False, 'message': f'Fix failed: {e}'}

    def analyze_issues(self, df, study, domain_code):
        """Analyze what issues exist in the data"""
        issues = []
        has_issues = False
        
        expected_studyid = study.study_number
        
        # Check STUDYID format
        if 'STUDYID' in df.columns:
            studyid_issues = df[df['STUDYID'] != expected_studyid]['STUDYID'].unique()
            if len(studyid_issues) > 0:
                has_issues = True
                issues.append(f"STUDYID format issues: {list(studyid_issues)}")
        
        # Check USUBJID format
        if 'USUBJID' in df.columns:
            usubjid_pattern = f"^{re.escape(expected_studyid)}-\\d{{3,}}$"
            invalid_usubjids = df[~df['USUBJID'].str.match(usubjid_pattern, na=False)]['USUBJID'].unique()
            if len(invalid_usubjids) > 0:
                has_issues = True
                issues.append(f"USUBJID format issues: {list(invalid_usubjids[:5])}{'...' if len(invalid_usubjids) > 5 else ''}")
        
        # Check for duplicate sequence numbers
        seq_col = f'{domain_code}SEQ'
        if seq_col in df.columns and 'USUBJID' in df.columns:
            duplicates = df.groupby('USUBJID')[seq_col].apply(lambda x: x.duplicated().any())
            if duplicates.any():
                has_issues = True
                issues.append("Duplicate sequence numbers within subjects")
        
        return {'has_issues': has_issues, 'issues': issues}

    def regenerate_xpt_file(self, df, domain_code):
        """Regenerate XPT file from DataFrame"""
        try:
            import pyreadstat
            import tempfile
            import os
            
            # Prepare DataFrame for SAS format
            df_sas = self.prepare_dataframe_for_sas(df, domain_code)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.xpt', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            try:
                # Write XPT file using pyreadstat
                pyreadstat.write_xport(
                    df_sas,
                    temp_path,
                    table_name=domain_code.upper()[:8],
                    file_format_version=5
                )
                
                # Read the generated file
                with open(temp_path, 'rb') as f:
                    xpt_content = f.read()
                
                return xpt_content
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except ImportError:
            # Fallback to CSV if pyreadstat not available
            return df.to_csv(index=False).encode('utf-8')
        except Exception as e:
            logger.error(f"Error generating XPT file: {e}")
            return None

    def prepare_dataframe_for_sas(self, df, domain_code):
        """Prepare DataFrame for SAS XPT format"""
        df_prepared = df.copy()
        
        # Ensure DOMAIN column exists and is set correctly
        df_prepared['DOMAIN'] = domain_code.upper()
        
        # SAS XPT format constraints
        MAX_STRING_LENGTH = 200
        MAX_COLUMN_NAME_LENGTH = 8
        
        # Fix column names for SAS compatibility
        column_mapping = {}
        for col in df_prepared.columns:
            # SAS column names: max 8 chars, start with letter, alphanumeric + underscore only
            clean_col = col.upper()
            clean_col = ''.join(c for c in clean_col if c.isalnum() or c == '_')
            if clean_col and not clean_col[0].isalpha():
                clean_col = 'C' + clean_col  # Prefix with C if starts with number
            clean_col = clean_col[:MAX_COLUMN_NAME_LENGTH]
            
            # Ensure uniqueness
            base_col = clean_col
            counter = 1
            while clean_col in column_mapping.values():
                clean_col = base_col[:6] + str(counter).zfill(2)
                counter += 1
                
            column_mapping[col] = clean_col
        
        df_prepared = df_prepared.rename(columns=column_mapping)
        
        # Fix data types and values
        for col in df_prepared.columns:
            if df_prepared[col].dtype == 'object':
                # String columns
                df_prepared[col] = df_prepared[col].astype(str)
                df_prepared[col] = df_prepared[col].replace(['nan', 'None', 'NaN'], '')
                df_prepared[col] = df_prepared[col].str[:MAX_STRING_LENGTH]
                # Remove any problematic characters
                df_prepared[col] = df_prepared[col].str.replace(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', regex=True)
            else:
                # Numeric columns - convert to float64 (SAS numeric type)
                df_prepared[col] = pd.to_numeric(df_prepared[col], errors='coerce')
                df_prepared[col] = df_prepared[col].astype('float64')
        
        # Fill NaN values appropriately
        for col in df_prepared.columns:
            if df_prepared[col].dtype == 'object':
                df_prepared[col] = df_prepared[col].fillna('')
            else:
                df_prepared[col] = df_prepared[col].fillna(0)
        
        # Ensure required CDISC columns are present and in correct order
        required_cols = ['STUDYID', 'DOMAIN', 'USUBJID']
        existing_cols = [col for col in required_cols if col in df_prepared.columns]
        other_cols = [col for col in df_prepared.columns if col not in required_cols]
        
        # Reorder columns: required first, then others
        final_cols = existing_cols + sorted(other_cols)
        df_prepared = df_prepared[final_cols]
        
        return df_prepared