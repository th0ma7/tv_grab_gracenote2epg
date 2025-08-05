"""
gracenote2epg.gracenote2epg_xmltv - XMLTV generation

Handles generation of XMLTV files with intelligent description formatting,
station information, and program details with multi-language support.
DTD-compliant version with optimized language detection caching.
"""

import codecs
import logging
import re
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .gracenote2epg_utils import CacheManager, TimeUtils, HtmlUtils
from .gracenote2epg_language import LanguageDetector


class XmltvGenerator:
    """Generates XMLTV files from parsed guide data"""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.station_count = 0
        self.episode_count = 0

        # Language detection is handled by LanguageDetector module
        self.language_detector: Optional[LanguageDetector] = None

    def generate_xmltv(self, schedule: Dict, config: Dict[str, Any],
                       xmltv_file: Path) -> bool:
        """Generate XMLTV file with automatic backup and optimized language detection"""
        try:
            logging.info('=== XMLTV Generation ===')

            # Initialize language detector with configuration
            langdetect_enabled = config.get('langdetect', True)
            self.language_detector = LanguageDetector(enabled=langdetect_enabled)

            # Load cache from previous XMLTV if language detection is enabled
            if langdetect_enabled:
                self.language_detector.load_cache_from_xmltv(xmltv_file)

            # Always backup existing XMLTV
            self.cache_manager.backup_xmltv(xmltv_file)

            # Generate new XMLTV
            encoding = 'utf-8'

            with codecs.open(xmltv_file, 'w+b', encoding=encoding) as f:
                self._print_header(f, encoding)
                self._print_stations(f, schedule)
                self._print_episodes(f, schedule, config)
                self._print_footer(f)

            # Log language statistics via detector
            if self.language_detector:
                self.language_detector.log_final_statistics()

            # Verify and log result
            if xmltv_file.exists():
                file_size = xmltv_file.stat().st_size
                logging.info('XMLTV file created: %s (%d bytes)', xmltv_file.name, file_size)
                return True
            else:
                logging.error('XMLTV file was not created: %s', xmltv_file)
                return False

        except Exception as e:
            logging.exception('Exception in XMLTV generation: %s', str(e))
            return False

    def _print_header(self, fh, encoding: str):
        """Print XMLTV header"""
        logging.info('Creating xmltv.xml file...')
        fh.write(f'<?xml version="1.0" encoding="{encoding}"?>\n')
        fh.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        fh.write('<tv source-info-url="http://tvschedule.gracenote.com/" source-info-name="gracenote.com">\n')

    def _print_footer(self, fh):
        """Print XMLTV footer"""
        fh.write('</tv>\n')

    def _print_stations(self, fh, schedule: Dict):
        """Print station/channel information"""
        self.station_count = 0

        try:
            logging.info('Writing Stations to xmltv.xml file...')

            # Sort stations by channel number, fallback to call sign
            try:
                schedule_sort = OrderedDict(sorted(
                    schedule.items(),
                    key=lambda x: int(x[1]['chnum'].split('.')[0]) if x[1].get('chnum', '').replace('.', '').isdigit() else float('inf')
                ))
            except (ValueError, TypeError):
                schedule_sort = OrderedDict(sorted(
                    schedule.items(),
                    key=lambda x: x[1].get('chfcc', '')
                ))

            for station_id, station_data in schedule_sort.items():
                fh.write(f'\t<channel id="{station_id}.gracenote2epg">\n')

                # TVheadend channel name (if available)
                if station_data.get('chtvh'):
                    tvh_name = HtmlUtils.conv_html(station_data['chtvh'])
                    fh.write(f'\t\t<display-name>{tvh_name}</display-name>\n')

                # Channel number and call sign
                if station_data.get('chnum') and station_data.get('chfcc'):
                    ch_num = station_data['chnum']
                    ch_fcc = station_data['chfcc']
                    ch_name = station_data.get('chnam', '')

                    fh.write(f'\t\t<display-name>{ch_num} {HtmlUtils.conv_html(ch_fcc)}</display-name>\n')

                    if ch_name and ch_name != "INDEPENDENT":
                        fh.write(f'\t\t<display-name>{HtmlUtils.conv_html(ch_name)}</display-name>\n')

                    fh.write(f'\t\t<display-name>{HtmlUtils.conv_html(ch_fcc)}</display-name>\n')
                    fh.write(f'\t\t<display-name>{ch_num}</display-name>\n')

                elif station_data.get('chfcc'):
                    ch_fcc = station_data['chfcc']
                    fh.write(f'\t\t<display-name>{HtmlUtils.conv_html(ch_fcc)}</display-name>\n')

                elif station_data.get('chnum'):
                    ch_num = station_data['chnum']
                    fh.write(f'\t\t<display-name>{ch_num}</display-name>\n')

                # Channel icon
                if station_data.get('chicon'):
                    icon_url = station_data['chicon']
                    if not icon_url.startswith('http'):
                        icon_url = f"http:{icon_url}"
                    fh.write(f'\t\t<icon src="{icon_url}" />\n')

                fh.write('\t</channel>\n')
                self.station_count += 1

        except Exception as e:
            logging.exception('Exception in _print_stations: %s', str(e))

    def _print_episodes(self, fh, schedule: Dict, config: Dict[str, Any]):
        """Print episode/program information - DTD compliant with optimized language detection"""
        self.episode_count = 0
        basic_desc_count = 0
        enhanced_desc_count = 0
        missing_desc_count = 0

        # Configuration values
        use_extended_desc = config.get('xdesc', False)      # Use extended series description
        use_extended_details = config.get('xdetails', False) # Add extra details (• S37E13 | CC)
        use_actor_photos = config.get('xdetails', False)    # Actor photos with extended details
        need_extended_download = use_extended_desc or use_extended_details  # Download if either is true
        safe_titles = config.get('stitle', False)
        ep_genre = config.get('epgenre', '3')
        ep_icon = config.get('epicon', '1')

        try:
            logging.info('Writing Episodes to xmltv.xml file...')
            logging.info('Configuration: xdesc=%s (use extended series description), xdetails=%s (add extra info)',
                        use_extended_desc, use_extended_details)
            if need_extended_download:
                logging.info('Extended details download enabled')
            else:
                logging.info('Using basic guide data only')

            # Count total episodes for progress tracking
            total_episodes = 0
            for station_id, station_data in schedule.items():
                for episode_key, episode_data in station_data.items():
                    if not episode_key.startswith("ch"):
                        if episode_data.get('epstart'):
                            total_episodes += 1

            logging.info('Total episodes to process: %d', total_episodes)

            # Progress tracking variables
            processed_episodes = 0
            last_progress_log = 0
            progress_interval = max(1, total_episodes // 20)  # Log every 5% (20 intervals)

            for station_id, station_data in schedule.items():
                for episode_key, episode_data in station_data.items():
                    if episode_key.startswith("ch"):  # Skip channel metadata
                        continue

                    try:
                        if not episode_data.get('epstart'):
                            continue

                        processed_episodes += 1

                        # Log progress every 5% or every 1000 episodes, whichever is smaller
                        if (processed_episodes - last_progress_log >= min(progress_interval, 1000) or
                            processed_episodes == total_episodes):
                            progress_percent = round((processed_episodes / total_episodes * 100)) if total_episodes > 0 else 0
                            logging.info('XMLTV generation progress: %d/%d episodes (%d%%)',
                                       processed_episodes, total_episodes, progress_percent)
                            last_progress_log = processed_episodes

                        # === PREPARATION PHASE - BEFORE ANY XML WRITING ===

                        # Time information
                        start_time = TimeUtils.conv_time(float(episode_data['epstart']))
                        stop_time = TimeUtils.conv_time(float(episode_data['epend'])) if episode_data.get('epend') else start_time
                        tz_offset = TimeUtils.get_timezone_offset()

                        # Detect language using the language detector with caching optimization
                        program_id = episode_data.get('epid', '')  # TMS ID unique
                        detected_language = 'en'  # Default

                        if self.language_detector:
                            # Priority 1: Try to detect from extended description if available
                            if use_extended_desc and need_extended_download:
                                extended_desc = episode_data.get('epseriesdesc')
                                if extended_desc and str(extended_desc).strip():
                                    detected_language = self.language_detector.detect_language(
                                        str(extended_desc), program_id)

                            # Priority 2: Detect from basic description
                            if detected_language == 'en':
                                basic_desc = episode_data.get('epdesc')
                                if basic_desc and str(basic_desc).strip():
                                    detected_language = self.language_detector.detect_language(
                                        str(basic_desc), program_id)

                        # Prepare final description
                        final_description = self._prepare_description(episode_data, detected_language,
                                                                    use_extended_desc, use_extended_details,
                                                                    need_extended_download)

                        if final_description:
                            enhanced_desc_count += 1
                        else:
                            missing_desc_count += 1

                        # === START XMLTV PROGRAMME - STRICT DTD ORDER ===

                        fh.write(f'\t<programme start="{start_time} {tz_offset}" stop="{stop_time} {tz_offset}" channel="{station_id}.gracenote2epg">\n')

                        # 1. TITLE+ (obligatoire)
                        if episode_data.get('epshow'):
                            show_title = HtmlUtils.conv_html(episode_data['epshow'])
                            fh.write(f'\t\t<title lang="{detected_language}">{show_title}</title>\n')

                        # 2. SUB-TITLE*
                        if episode_data.get('eptitle'):
                            episode_title = HtmlUtils.conv_html(episode_data['eptitle'])
                            if safe_titles:
                                episode_title = re.sub(r'[\\/*?:|]', "_", episode_title)
                            fh.write(f'\t\t<sub-title lang="{detected_language}">{episode_title}</sub-title>\n')

                        # 3. DESC*
                        if final_description:
                            fh.write(f'\t\t<desc lang="{detected_language}">{HtmlUtils.conv_html(final_description)}</desc>\n')

                        # 4. CREDITS? (DTD compliant - no src attribute)
                        self._write_credits_dtd_compliant(fh, episode_data)

                        # 5. DATE?
                        if episode_data.get('epyear'):
                            fh.write(f'\t\t<date>{episode_data["epyear"]}</date>\n')

                        # 6. CATEGORY* (all categories together)
                        self._write_categories(fh, episode_data, ep_genre)

                        # 7-9. KEYWORD*, LANGUAGE?, ORIG-LANGUAGE? (not used)

                        # 10. LENGTH?
                        if episode_data.get('eplength'):
                            fh.write(f'\t\t<length units="minutes">{episode_data["eplength"]}</length>\n')

                        # 11. ICON*
                        self._write_program_icons(fh, episode_data, ep_icon, episode_key)

                        # 12-13. URL*, COUNTRY* (not used)

                        # 14. EPISODE-NUM* (ALL episode numbers here, nowhere else!)
                        dd_progid = episode_data.get('epid', '')
                        if dd_progid and len(dd_progid) >= 4:
                            fh.write(f'\t\t<episode-num system="dd_progid">{dd_progid[:-4]}.{dd_progid[-4:]}</episode-num>\n')

                        if episode_data.get('epsn') and episode_data.get('epen'):
                            season = str(episode_data['epsn']).zfill(2)
                            episode_num = str(episode_data['epen']).zfill(2)
                            fh.write(f'\t\t<episode-num system="onscreen">S{season}E{episode_num}</episode-num>\n')

                            # XMLTV numbering (zero-based)
                            season_xmltv = int(episode_data['epsn']) - 1
                            episode_xmltv = int(episode_data['epen']) - 1
                            fh.write(f'\t\t<episode-num system="xmltv_ns">{season_xmltv}.{episode_xmltv}.</episode-num>\n')

                        # 15-16. VIDEO?, AUDIO? (not used)

                        # 17. PREVIOUSLY-SHOWN?
                        if not self._is_new_or_live(episode_data):
                            fh.write('\t\t<previously-shown')
                            if episode_data.get('epoad') and int(episode_data['epoad']) > 0:
                                orig_time = TimeUtils.conv_time(float(episode_data['epoad']))
                                fh.write(f' start="{orig_time} {tz_offset}"')
                            fh.write(' />\n')

                        # 18. PREMIERE?
                        flags = episode_data.get('epflag', [])
                        if isinstance(flags, (list, tuple)) and 'Premiere' in flags:
                            fh.write('\t\t<premiere />\n')

                        # 19. LAST-CHANCE?
                        if isinstance(flags, (list, tuple)) and 'Finale' in flags:
                            fh.write('\t\t<last-chance />\n')

                        # 20. NEW?
                        if isinstance(flags, (list, tuple)) and 'New' in flags:
                            fh.write('\t\t<new />\n')

                        # 21. SUBTITLES*
                        if episode_data.get('eptags') and 'CC' in episode_data['eptags']:
                            fh.write('\t\t<subtitles type="teletext" />\n')

                        # 22. RATING*
                        if episode_data.get('eprating'):
                            fh.write(f'\t\t<rating>\n\t\t\t<value>{episode_data["eprating"]}</value>\n\t\t</rating>\n')

                        # 23. STAR-RATING*
                        if episode_data.get('epstar'):
                            fh.write(f'\t\t<star-rating>\n\t\t\t<value>{episode_data["epstar"]}/4</value>\n\t\t</star-rating>\n')

                        # 24-25. REVIEW*, IMAGE* (not used)

                        fh.write('\t</programme>\n')
                        self.episode_count += 1

                    except Exception as e:
                        logging.exception('Error processing episode %s: %s', episode_key, str(e))

            # Log statistics
            logging.info('Description statistics: Episodes=%d, Enhanced_desc=%d, Missing_desc=%d',
                        self.episode_count, enhanced_desc_count, missing_desc_count)

            if use_extended_details:
                logging.info('Extended details added to episodes (• info format)')
            if use_extended_desc:
                logging.info('Extended series descriptions used when available')
            if not use_extended_details and not use_extended_desc:
                logging.info('Basic guide data only (no extended features)')

            # Report missing descriptions
            if missing_desc_count > 0:
                logging.info('Missing descriptions: %d episodes', missing_desc_count)

        except Exception as e:
            logging.exception('Exception in _print_episodes: %s', str(e))

    def _prepare_description(self, episode_data: Dict, detected_language: str,
                           use_extended_desc: bool, use_extended_details: bool,
                           need_extended_download: bool) -> Optional[str]:
        """Prepare final description based on xdesc and xdetails settings"""
        try:
            # Step 1: Determine base description source
            base_description = None

            if use_extended_desc and need_extended_download:
                # Try extended series description first (from downloaded details)
                extended_desc = episode_data.get('epseriesdesc')
                if extended_desc and str(extended_desc).strip():
                    base_description = str(extended_desc).strip()
                    logging.debug('Using extended series description for %s',
                                 episode_data.get('epshow', 'Unknown'))
                else:
                    # Fallback to basic description from guide
                    basic_desc = episode_data.get('epdesc')  # This is shortDesc from JSON
                    base_description = str(basic_desc).strip() if basic_desc else ''
                    logging.debug('Extended description not available, using basic for %s',
                                 episode_data.get('epshow', 'Unknown'))
            else:
                # Use basic description from guide (shortDesc)
                basic_desc = episode_data.get('epdesc')  # This is shortDesc from JSON
                base_description = str(basic_desc).strip() if basic_desc else ''
                logging.debug('Using basic guide description for %s',
                             episode_data.get('epshow', 'Unknown'))

            # Step 2: Add extended details if xdetails=true
            if base_description:
                if use_extended_details:
                    # Add extra info (• S37E13 | CC, year, rating, etc.) from guide data
                    return self._add_enhanced_info_to_basic_desc(
                        base_description, episode_data, detected_language)
                else:
                    # Use description as-is (no • S37E13 | CC)
                    return base_description

            return None

        except Exception as e:
            logging.warning('Error preparing description for episode %s: %s',
                          episode_data.get('epid', 'unknown'), str(e))
            return None

    def _add_enhanced_info_to_basic_desc(self, base_desc: str, episode_data: Dict, language: str) -> str:
        """Add enhanced info (with translations) to basic description"""
        try:
            # Build additional info with translations
            additional_info = []

            # Add year for movies/shows
            if episode_data.get('epyear') and str(episode_data['epyear']) != '0':
                additional_info.append(str(episode_data['epyear']))

            # Add season/episode info for series
            if episode_data.get('epsn') and episode_data.get('epen'):
                try:
                    season_ep = f"S{int(episode_data['epsn']):02d}E{int(episode_data['epen']):02d}"
                    additional_info.append(season_ep)
                except (ValueError, TypeError):
                    pass

            # Add premiere date if available
            if episode_data.get('epoad') and str(episode_data['epoad']).isdigit() and int(episode_data['epoad']) > 0:
                try:
                    is_dst = time.daylight and time.localtime().tm_isdst > 0
                    tz_offset_seconds = (time.altzone if is_dst else time.timezone)
                    orig_date = int(episode_data['epoad']) + tz_offset_seconds
                    premiere_date = datetime.fromtimestamp(orig_date).strftime('%Y-%m-%d')
                    # Use language detector for translation
                    premiered_text = self.language_detector.get_translated_term('premiered', language) if self.language_detector else 'Premiered'
                    additional_info.append(f"{premiered_text}: {premiere_date}")
                except (ValueError, TypeError, OSError):
                    pass

            # Add rating if available
            if episode_data.get('eprating') and str(episode_data['eprating']).strip():
                # Use language detector for translation
                rated_text = self.language_detector.get_translated_term('rated', language) if self.language_detector else 'Rated'
                additional_info.append(f"{rated_text}: {episode_data['eprating']}")

            # Add flags with translations (DTD compliant - all in description)
            flags = []
            if episode_data.get('epflag') and isinstance(episode_data['epflag'], (list, tuple)):
                if 'New' in episode_data['epflag']:
                    new_text = self.language_detector.get_translated_term('new', language) if self.language_detector else 'NEW'
                    flags.append(new_text)
                if 'Live' in episode_data['epflag']:
                    live_text = self.language_detector.get_translated_term('live', language) if self.language_detector else 'LIVE'
                    flags.append(live_text)
                if 'Premiere' in episode_data['epflag']:
                    premiere_text = self.language_detector.get_translated_term('premiere', language) if self.language_detector else 'PREMIERE'
                    flags.append(premiere_text)
                if 'Finale' in episode_data['epflag']:
                    finale_text = self.language_detector.get_translated_term('finale', language) if self.language_detector else 'FINALE'
                    flags.append(finale_text)

            if episode_data.get('eptags') and isinstance(episode_data['eptags'], (list, tuple)):
                if 'CC' in episode_data['eptags']:
                    flags.append('CC')
                if 'HD' in episode_data['eptags']:
                    flags.append('HD')

            if flags:
                additional_info.append(' | '.join(flags))

            # Use bullet point instead of newline (like zap2epg, DTD compliant)
            if additional_info:
                info_str = ' | '.join(additional_info)
                enhanced_description = f"{base_desc} • {info_str}"
                logging.debug('Enhanced description created for %s: added %d info items in %s',
                             episode_data.get('epshow', 'Unknown'), len(additional_info), language)
                return enhanced_description

            return base_desc

        except Exception as e:
            logging.warning('Error enhancing basic description for episode %s: %s',
                          episode_data.get('epid', 'unknown'), str(e))
            return base_desc

    def _write_credits_dtd_compliant(self, fh, episode_data: Dict, use_actor_photos: bool = True):
        """Write cast and crew credits - DTD compliant"""
        credits = episode_data.get('epcredits')
        if credits and isinstance(credits, list):
            fh.write('\t\t<credits>\n')

            # Valid DTD roles in order: director, actor, writer, adapter, producer, composer, editor, presenter, commentator, guest
            valid_roles = {
                'director': 'director',
                'actor': 'actor',
                'writer': 'writer',
                'adapter': 'adapter',
                'producer': 'producer',
                'composer': 'composer',
                'editor': 'editor',
                'presenter': 'presenter',
                'commentator': 'commentator',
                'guest': 'guest',
                'voice': 'actor',  # Map voice actors to actor (DTD compliant)
                'narrator': 'presenter',  # Map narrator to presenter
                'host': 'presenter',  # Map host to presenter
            }

            for credit in credits:
                if isinstance(credit, dict):
                    original_role = credit.get('role', '').lower()
                    name = credit.get('name', '')
                    character = credit.get('characterName', '')
                    asset_id = credit.get('assetId', '')

                    # Map to valid DTD role
                    if original_role in valid_roles:
                        dtd_role = valid_roles[original_role]

                        if dtd_role and name:
                            # Build the credit tag with photo if available
                            if use_actor_photos and asset_id and character:
                                # With photo and character name
                                photo_url = f"https://zap2it.tmsimg.com/assets/{asset_id}.jpg"
                                fh.write(f'\t\t\t<{dtd_role} role="{HtmlUtils.conv_html(character)}" src="{photo_url}">{HtmlUtils.conv_html(name)}</{dtd_role}>\n')
                                logging.debug('Added actor photo for %s (%s)', name, character)
                            elif use_actor_photos and asset_id:
                                # With photo but no character name
                                photo_url = f"https://zap2it.tmsimg.com/assets/{asset_id}.jpg"
                                fh.write(f'\t\t\t<{dtd_role} src="{photo_url}">{HtmlUtils.conv_html(name)}</{dtd_role}>\n')
                                logging.debug('Added actor photo for %s', name)
                            elif character:
                                # With character name but no photo (or photos disabled)
                                fh.write(f'\t\t\t<{dtd_role} role="{HtmlUtils.conv_html(character)}">{HtmlUtils.conv_html(name)}</{dtd_role}>\n')
                            else:
                                # Name only
                                fh.write(f'\t\t\t<{dtd_role}>{HtmlUtils.conv_html(name)}</{dtd_role}>\n')
                    else:
                        # Skip unsupported roles
                        logging.debug('Skipping unsupported credit role: %s for %s', original_role, name)

            fh.write('\t\t</credits>\n')

    def _write_program_icons(self, fh, episode_data: Dict, ep_icon: str, episode_key: str):
        """Write program icon information"""
        if episode_key.startswith("MV"):  # Movie
            if episode_data.get('epthumb'):
                fh.write(f'\t\t<icon src="https://zap2it.tmsimg.com/assets/{episode_data["epthumb"]}.jpg" />\n')
        else:  # TV Show
            if ep_icon == '1':  # Series + episode icons
                if episode_data.get('epimage'):
                    fh.write(f'\t\t<icon src="https://zap2it.tmsimg.com/assets/{episode_data["epimage"]}.jpg" />\n')
                elif episode_data.get('epthumb'):
                    fh.write(f'\t\t<icon src="https://zap2it.tmsimg.com/assets/{episode_data["epthumb"]}.jpg" />\n')
            elif ep_icon == '2':  # Episode icons only
                if episode_data.get('epthumb'):
                    fh.write(f'\t\t<icon src="https://zap2it.tmsimg.com/assets/{episode_data["epthumb"]}.jpg" />\n')

    def _is_new_or_live(self, episode_data: Dict) -> bool:
        """Check if episode is new or live"""
        flags = episode_data.get('epflag', [])
        if isinstance(flags, (list, tuple)):
            return any(flag in ['New', 'Live'] for flag in flags)
        return False

    def _write_categories(self, fh, episode_data: Dict, ep_genre: str):
        """Write program categories/genres"""
        if ep_genre == '0':  # No genres
            return

        genres = self._get_genre_list(episode_data, ep_genre)
        if genres:
            for genre in genres:
                clean_genre = HtmlUtils.conv_html(genre).replace('filter-', '')
                fh.write(f'\t\t<category lang="en">{clean_genre}</category>\n')

    def _get_genre_list(self, episode_data: Dict, ep_genre: str) -> List[str]:
        """Get processed genre list based on configuration"""
        ep_filter = episode_data.get('epfilter', [])
        ep_genres = episode_data.get('epgenres', [])

        if not isinstance(ep_filter, list):
            ep_filter = []
        if not isinstance(ep_genres, list):
            ep_genres = []

        if ep_genre == '1':  # Primary genre only
            return self._get_primary_genre(ep_filter, ep_genres)
        elif ep_genre == '2':  # EIT categories
            return self._get_eit_genres(ep_filter, ep_genres)
        elif ep_genre == '3':  # All genres
            return ep_genres if ep_genres else ep_filter

        return []

    def _get_primary_genre(self, ep_filter: List, ep_genres: List) -> List[str]:
        """Get primary genre mapping"""
        genres = ep_genres if ep_genres else ep_filter

        for genre in genres:
            if 'Movie' in genre or 'movie' in genre:
                return ["Movie / Drama"]
            elif 'News' in genre:
                return ["News / Current affairs"]
            elif 'Sports' in genre:
                return ["Sports"]
            elif 'Talk' in genre:
                return ["Talk show"]
            elif 'Game show' in genre:
                return ["Game show / Quiz / Contest"]
            elif 'Children' in genre:
                return ["Children's / Youth programs"]
            elif 'Sitcom' in genre:
                return ["Variety show"]

        return ["Variety show"]  # Default

    def _get_eit_genres(self, ep_filter: List, ep_genres: List) -> List[str]:
        """Get EIT-style genre mapping"""
        genre_list = []
        all_genres = ep_genres if ep_genres else ep_filter

        # Complex EIT mapping logic (simplified)
        for genre in all_genres:
            if genre != "Comedy":
                genre_list.append(genre)

        # Apply EIT transformations
        if any('Movie' in g for g in genre_list):
            genre_list.insert(0, "Movie / Drama")
        if any('News' in g for g in genre_list):
            genre_list.insert(0, "News / Current affairs")
        # Add more EIT mappings as needed

        return genre_list
