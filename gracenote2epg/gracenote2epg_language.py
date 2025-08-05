"""
gracenote2epg.gracenote2epg_language - Language detection and caching

Handles language detection with intelligent caching for performance optimization.
Supports French, English, and Spanish with automatic detection and translation.
"""

import hashlib
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Tuple


class LanguageCache:
    """Intelligent cache for language detection results"""
    
    def __init__(self):
        self.program_language_cache: Dict[str, str] = {}  # program_id -> language
        self.description_hash_cache: Dict[str, str] = {}  # desc_hash -> language
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_lookups = 0
        
    def load_from_previous_xmltv(self, xmltv_file: Path) -> bool:
        """Load language cache from previous XMLTV file"""
        if not xmltv_file.exists():
            logging.info('No previous XMLTV file found - starting with empty language cache')
            return False
        
        try:
            logging.info('Loading language cache from previous XMLTV file...')
            tree = ET.parse(xmltv_file)
            root = tree.getroot()
            
            program_count = 0
            language_stats = {'fr': 0, 'en': 0, 'es': 0, 'other': 0}
            
            for programme in root.findall('programme'):
                # Extract program ID from episode-num dd_progid
                program_id = None
                for episode_num in programme.findall('episode-num'):
                    if episode_num.get('system') == 'dd_progid':
                        program_id = episode_num.text
                        if program_id and '.' in program_id:
                            program_id = program_id.replace('.', '')  # Remove dot format
                        break
                
                if not program_id:
                    continue
                
                # Extract language from desc element
                desc_elem = programme.find('desc')
                if desc_elem is not None:
                    detected_lang = desc_elem.get('lang', 'en')
                    desc_text = desc_elem.text or ''
                    
                    # Cache by program_id
                    self.program_language_cache[program_id] = detected_lang
                    
                    # Cache by description hash for better accuracy
                    if desc_text.strip():
                        desc_hash = self._hash_description(desc_text)
                        self.description_hash_cache[desc_hash] = detected_lang
                    
                    # Statistics
                    if detected_lang in language_stats:
                        language_stats[detected_lang] += 1
                    else:
                        language_stats['other'] += 1
                    
                    program_count += 1
            
            logging.info('Language cache loaded: %d programs cached', program_count)
            if program_count > 0:
                logging.debug('Previous language distribution:')
                for lang, count in language_stats.items():
                    if count > 0:
                        percentage = (count / program_count) * 100
                        lang_name = {'fr': 'French', 'en': 'English', 'es': 'Spanish', 'other': 'Other'}[lang]
                        logging.debug('  %s: %d programs (%.1f%%)', lang_name, count, percentage)
            
            return True
            
        except Exception as e:
            logging.warning('Error loading language cache from XMLTV: %s', str(e))
            return False
    
    def _hash_description(self, description: str) -> str:
        """Create MD5 hash of description to identify identical content"""
        normalized = ' '.join(description.strip().split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:16]  # 16 chars sufficient
    
    def get_cached_language(self, program_id: str, description: str = '') -> Optional[str]:
        """
        Get cached language if available
        
        Args:
            program_id: Program ID (epid)
            description: Program description for hash verification
            
        Returns:
            Detected language or None if not cached
        """
        self.total_lookups += 1
        
        # Priority 1: Cache by program_id
        if program_id and program_id in self.program_language_cache:
            self.cache_hits += 1
            logging.debug('Language cache HIT (program_id): %s -> %s', 
                         program_id, self.program_language_cache[program_id])
            return self.program_language_cache[program_id]
        
        # Priority 2: Cache by description hash
        if description and description.strip():
            desc_hash = self._hash_description(description)
            if desc_hash in self.description_hash_cache:
                self.cache_hits += 1
                logging.debug('Language cache HIT (desc_hash): %s -> %s', 
                             desc_hash[:8], self.description_hash_cache[desc_hash])
                return self.description_hash_cache[desc_hash]
        
        # Cache miss
        self.cache_misses += 1
        logging.debug('Language cache MISS: %s', program_id or 'no_id')
        return None
    
    def cache_language(self, program_id: str, description: str, detected_language: str):
        """Cache a detected language for future use"""
        if program_id:
            self.program_language_cache[program_id] = detected_language
        
        if description and description.strip():
            desc_hash = self._hash_description(description)
            self.description_hash_cache[desc_hash] = detected_language
        
        logging.debug('Language cached: %s -> %s', program_id or 'no_id', detected_language)
    
    def get_cache_stats(self) -> Dict[str, float]:
        """Return cache performance statistics"""
        cache_efficiency = (self.cache_hits / self.total_lookups * 100) if self.total_lookups > 0 else 0
        return {
            'total_lookups': self.total_lookups,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_efficiency': cache_efficiency,
            'cached_programs': len(self.program_language_cache),
            'cached_descriptions': len(self.description_hash_cache)
        }


class LanguageDetector:
    """Language detection with caching and translation support"""
    
    # Translation dictionaries for different languages  
    TRANSLATIONS = {
        'en': {
            'rated': 'Rated',
            'new': 'NEW',
            'premiere': 'PREMIERE',
            'finale': 'FINALE',
            'live': 'LIVE',
            'premiered': 'Premiered'
        },
        'fr': {
            'rated': 'Classé',
            'new': 'NOUVEAU',
            'premiere': 'PREMIÈRE',
            'finale': 'FINALE',
            'live': 'EN DIRECT',
            'premiered': 'Première diffusion'
        },
        'es': {
            'rated': 'Clasificado',
            'new': 'NUEVO',
            'premiere': 'ESTRENO',
            'finale': 'FINAL',
            'live': 'EN VIVO',
            'premiered': 'Estrenado'
        }
    }
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.available = self._check_langdetect_availability()
        self.cache = LanguageCache()
        
        # Language statistics
        self.language_stats = {'fr': 0, 'en': 0, 'es': 0}
        
        # Log configuration
        if self.enabled and self.available:
            logging.info('Language detection: Using langdetect library with cache optimization')
        elif self.enabled and not self.available:
            logging.warning('Language detection: langdetect requested but not available')
            logging.warning('  Please install langdetect: pip install langdetect')
            logging.info('Language detection: Disabled - defaulting to English for all content')
            self.enabled = False
        else:
            logging.info('Language detection: Disabled by configuration - defaulting to English')
    
    def _check_langdetect_availability(self) -> bool:
        """Check if langdetect library is available"""
        try:
            from langdetect import detect
            return True
        except ImportError:
            return False
    
    def load_cache_from_xmltv(self, xmltv_file: Path) -> bool:
        """Load language cache from previous XMLTV file"""
        if self.enabled and self.available:
            return self.cache.load_from_previous_xmltv(xmltv_file)
        return False
    
    def detect_language(self, text: str, program_id: str = '') -> str:
        """
        Detect language with caching optimization
        
        Args:
            text: Text to analyze
            program_id: Program ID for cache optimization
            
        Returns:
            Detected language code (fr, en, es)
        """
        if not text or not isinstance(text, str):
            return 'en'
        
        # Return English if detection disabled
        if not (self.enabled and self.available):
            return 'en'
        
        # Check cache first (with program_id if available)
        cached_lang = self.cache.get_cached_language(program_id, text)
        if cached_lang:
            self.language_stats[cached_lang] += 1
            return cached_lang
        
        # Cache miss: perform expensive detection
        detected_lang = self._perform_detection(text)
        
        # Cache the result
        self.cache.cache_language(program_id, text, detected_lang)
        
        # Update statistics
        self.language_stats[detected_lang] += 1
        
        return detected_lang
    
    def _perform_detection(self, text: str) -> str:
        """Perform actual langdetect detection"""
        try:
            from langdetect import detect, LangDetectException
            try:
                detected = detect(text)
                if detected in ['fr', 'en', 'es']:
                    logging.debug('Language detected: %s for "%s"', detected, text[:50])
                    return detected
                else:
                    # Unsupported language, default to English
                    logging.debug('Unsupported language "%s" detected, defaulting to English', detected)
                    return 'en'
            except LangDetectException:
                # Detection failed (text too short, ambiguous, etc.)
                logging.debug('langdetect failed for text "%s", defaulting to English', text[:50])
                return 'en'
        except ImportError:
            # This shouldn't happen since we checked availability
            logging.debug('langdetect import error, defaulting to English')
            return 'en'
    
    def get_translated_term(self, term: str, language: str) -> str:
        """Get translated term for the detected language"""
        if language in self.TRANSLATIONS and term in self.TRANSLATIONS[language]:
            return self.TRANSLATIONS[language][term]
        # Fallback to English
        return self.TRANSLATIONS['en'].get(term, term.upper())
    
    def get_language_stats(self) -> Dict[str, int]:
        """Get language detection statistics"""
        return self.language_stats.copy()
    
    def get_cache_stats(self) -> Dict[str, float]:
        """Get cache performance statistics"""
        return self.cache.get_cache_stats()
    
    def log_final_statistics(self):
        """Log final language detection and cache statistics"""
        total_episodes = sum(self.language_stats.values())
        
        if total_episodes > 0:
            if self.enabled:
                logging.info('Language detection statistics (using langdetect library with cache):')
                for lang, count in self.language_stats.items():
                    percentage = (count / total_episodes) * 100
                    lang_name = {'fr': 'French', 'en': 'English', 'es': 'Spanish'}[lang]
                    logging.info('  %s: %d episodes (%.1f%%)', lang_name, count, percentage)
                
                # Cache performance statistics
                cache_stats = self.get_cache_stats()
                logging.info('Language cache performance:')
                logging.info('  Cache efficiency: %.1f%% (%d hits / %d lookups)', 
                           cache_stats['cache_efficiency'], 
                           cache_stats['cache_hits'], 
                           cache_stats['total_lookups'])
                
                if cache_stats['total_lookups'] > 0:
                    time_saved_estimate = cache_stats['cache_hits'] * 0.05  # ~50ms per detection avoided
                    logging.info('  Estimated time saved: %.1f seconds', time_saved_estimate)
                    
                    if cache_stats['cache_efficiency'] > 70:
                        logging.info('  Excellent cache performance - most language detections were reused!')
                    elif cache_stats['cache_efficiency'] > 30:
                        logging.info('  Good cache performance - significant time savings')
                    else:
                        logging.info('  Low cache efficiency - mostly new content or first run')
            else:
                logging.info('Language detection disabled - all content marked as English')
