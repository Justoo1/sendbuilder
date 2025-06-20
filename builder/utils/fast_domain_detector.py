import re
import logging
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import multiprocessing as mp
from dataclasses import dataclass
import time
from .patterns import DOMAIN_PATTERNS

logger = logging.getLogger(__name__)


@dataclass
class PageDetectionResult:
    """Result of page detection for a domain"""
    domain: str
    detected: bool
    confidence: float
    pages: List[int]
    method: str
    processing_time: float


class FastPageDetector:
    """
    Optimized page detection using parallel processing and pattern matching
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        # Limit max_workers to prevent resource exhaustion
        self.max_workers = max_workers or min(4, mp.cpu_count())
        
        # Use the actual domain patterns from the project
        self._load_domain_patterns()
    
    def _load_domain_patterns(self):
        """Load and prepare domain patterns from the main patterns file"""
        self.domain_patterns = {}
        
        for domain, info in DOMAIN_PATTERNS.items():
            # Extract patterns and create optimized version
            patterns = info.get('patterns', [])
            name = info.get('name', domain)
            
            # Create keywords from the domain name
            keywords = [name.lower()]
            if ' ' in name:
                keywords.extend(name.lower().split())
            
            # Add common terms based on domain type
            domain_keywords = {
                'DM': ['demographics', 'animal', 'subject'],
                'BW': ['body weight', 'weight', 'mass'],
                'CL': ['clinical', 'observation', 'signs'],
                'LB': ['laboratory', 'test', 'pathology'],
                'EG': ['ecg', 'electrocardiogram', 'cardiac'],
                'MA': ['macroscopic', 'gross', 'necropsy'],
                'MI': ['microscopic', 'histopathology'],
                'OM': ['organ', 'weight', 'measurement'],
                'FW': ['food', 'water', 'consumption'],
                'CV': ['cardiovascular', 'blood pressure'],
                'VS': ['vital signs', 'temperature', 'respiratory'],
                'DS': ['disposition', 'death', 'mortality']
            }
            
            if domain in domain_keywords:
                keywords.extend(domain_keywords[domain])
            
            self.domain_patterns[domain] = {
                'keywords': list(set(keywords)),  # Remove duplicates
                'patterns': patterns,
                'weight': 0.8  # Default weight
            }
    
    @lru_cache(maxsize=1000)
    def _cached_pattern_search(self, text: str, pattern: str) -> bool:
        """Cached pattern search for repeated patterns"""
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            logger.warning(f"Invalid regex pattern: {pattern}")
            return False
    
    def detect_domain_in_page(self, domain: str, page_text: str, page_num: int) -> Tuple[bool, float]:
        """
        Fast domain detection in a single page
        
        Args:
            domain (str): Domain code to search for
            page_text (str): Text content of the page
            page_num (int): Page number
            
        Returns:
            Tuple[bool, float]: (detected, confidence_score)
        """
        if not page_text or not page_text.strip():
            return False, 0.0
            
        if domain not in self.domain_patterns:
            logger.warning(f"Domain {domain} not found in patterns")
            return False, 0.0
        
        domain_config = self.domain_patterns[domain]
        confidence = 0.0
        
        # Check keywords (faster than regex)
        text_lower = page_text.lower()
        for keyword in domain_config['keywords']:
            if keyword in text_lower:
                confidence += 0.3
                if confidence >= 0.6:  # Early exit if high confidence
                    break
        
        # Check patterns only if needed
        if confidence < 0.6:
            for pattern in domain_config['patterns']:
                if self._cached_pattern_search(page_text, pattern):
                    confidence += 0.4
                    if confidence >= 0.8:  # Early exit if very high confidence
                        break
        
        # Weight adjustment
        confidence *= domain_config['weight']
        
        # Bonus for multiple indicators
        if confidence > 0.5:
            confidence += 0.1
        
        detected = confidence > 0.3
        return detected, min(1.0, confidence)
    
    def detect_domains_parallel(self, text_by_page: Dict[int, str], 
                              domains: List[str]) -> Dict[str, PageDetectionResult]:
        """
        Detect multiple domains across pages in parallel
        
        Args:
            text_by_page (Dict[int, str]): Dictionary mapping page numbers to text
            domains (List[str]): List of domains to detect
            
        Returns:
            Dict[str, PageDetectionResult]: Detection results by domain
        """
        start_time = time.time()
        
        results = {}
        
        # Validate inputs
        if not text_by_page or not domains:
            logger.warning("Empty input provided to detect_domains_parallel")
            for domain in domains:
                results[domain] = PageDetectionResult(
                    domain=domain,
                    detected=False,
                    confidence=0.0,
                    pages=[],
                    method='empty_input',
                    processing_time=0.0
                )
            return results
        
        # Create detection tasks
        detection_tasks = []
        for domain in domains:
            if domain not in self.domain_patterns:
                logger.warning(f"Skipping unknown domain: {domain}")
                continue
                
            for page_num, page_text in text_by_page.items():
                detection_tasks.append((domain, page_text, page_num))
        
        if not detection_tasks:
            logger.warning("No valid detection tasks created")
            for domain in domains:
                results[domain] = PageDetectionResult(
                    domain=domain,
                    detected=False,
                    confidence=0.0,
                    pages=[],
                    method='no_tasks',
                    processing_time=0.0
                )
            return results
        
        # Parallel execution with error handling
        domain_results = {domain: {'pages': [], 'confidences': []} for domain in domains}
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {}
                for domain, text, page in detection_tasks:
                    try:
                        future = executor.submit(self.detect_domain_in_page, domain, text, page)
                        future_to_task[future] = (domain, page)
                    except Exception as e:
                        logger.error(f"Error submitting task for {domain} page {page}: {e}")
                
                # Collect results with timeout
                for future in as_completed(future_to_task, timeout=30):  # 30 second timeout
                    domain, page_num = future_to_task[future]
                    try:
                        detected, confidence = future.result(timeout=5)  # 5 second per task timeout
                        if detected:
                            domain_results[domain]['pages'].append(page_num)
                            domain_results[domain]['confidences'].append(confidence)
                    except Exception as e:
                        logger.error(f"Error getting result for {domain} page {page_num}: {e}")
        
        except Exception as e:
            logger.error(f"Error in parallel execution: {e}")
            # Continue with whatever results we have
        
        # Compile final results
        processing_time = time.time() - start_time
        
        for domain in domains:
            pages = sorted(domain_results[domain]['pages'])
            confidences = domain_results[domain]['confidences']
            avg_confidence = sum(confidences) / max(1, len(confidences))
            
            results[domain] = PageDetectionResult(
                domain=domain,
                detected=len(pages) > 0,
                confidence=avg_confidence,
                pages=pages,
                method='parallel_pattern_matching',
                processing_time=processing_time / len(domains)
            )
        
        total_detected = sum(1 for r in results.values() if r.detected)
        logger.info(f"Detected {total_detected} domains for {len(domains)} domains across {len(text_by_page)} pages in {processing_time:.2f}s")
        return results