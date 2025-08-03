"""
gracenote2epg.gracenote2epg_xmltv - XMLTV generation

Handles generation of XMLTV files with intelligent description formatting,
station information, and program details.
"""

import codecs
import logging
import re
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from .gracenote2epg_utils import CacheManager, TimeUtils, HtmlUtils


class XmltvGenerator:
    """Generates XMLTV files from parsed guide data"""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.station_count = 0
        self.episode_count = 0

    def generate_xmltv(self, schedule: Dict, config: Dict[str, Any],
                       xmltv_file: Path) -> bool:
        """Generate XMLTV file with automatic backup"""
        try:
            logging.info('=== XMLTV Generation ===')

            # Always backup existing XMLTV
            self.cache_manager.backup_xmltv(xmltv_file)

            # Generate new XMLTV
            encoding = 'utf-8'

            with codecs.open(xmltv_file, 'w+b', encoding=encoding) as f:
                self._print_header(f, encoding)
                self._print_stations(f, schedule)
                self._print_episodes(f, schedule, config)
                self._print_footer(f)

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
        """Print episode/program information"""
        self.episode_count = 0
        basic_desc_count = 0
        enhanced_desc_count = 0
        missing_desc_count = 0
        missing_desc_programs = {}

        # Configuration values
        use_extended_desc = config.get('xdesc', False)
        need_extended_download = config.get('xdetails', False) or config.get('xdesc', False)
        safe_titles = config.get('stitle', False)
        ep_genre = config.get('epgenre', '3')
        ep_icon = config.get('epicon', '1')

        try:
            logging.info('Writing Episodes to xmltv.xml file...')
            if use_extended_desc:
                logging.info('Enhanced descriptions enabled (using extended data when available)')
            else:
                logging.info('Using basic descriptions only (from TV guide)')

            for station_id, station_data in schedule.items():
                for episode_key, episode_data in station_data.items():
                    if episode_key.startswith("ch"):  # Skip channel metadata
                        continue

                    try:
                        if not episode_data.get('epstart'):
                            continue

                        # Time information
                        start_time = TimeUtils.conv_time(float(episode_data['epstart']))
                        stop_time = TimeUtils.conv_time(float(episode_data['epend'])) if episode_data.get('epend') else start_time
                        tz_offset = TimeUtils.get_timezone_offset()

                        fh.write(f'\t<programme start="{start_time} {tz_offset}" stop="{stop_time} {tz_offset}" channel="{station_id}.gracenote2epg">\n')

                        # Episode number system
                        dd_progid = episode_data.get('epid', '')
                        if dd_progid and len(dd_progid) >= 4:
                            fh.write(f'\t\t<episode-num system="dd_progid">{dd_progid[:-4]}.{dd_progid[-4:]}</episode-num>\n')

                        # Title
                        if episode_data.get('epshow'):
                            show_title = HtmlUtils.conv_html(episode_data['epshow'])
                            fh.write(f'\t\t<title lang="en">{show_title}</title>\n')

                        # Sub-title
                        if episode_data.get('eptitle'):
                            episode_title = HtmlUtils.conv_html(episode_data['eptitle'])
                            if safe_titles:
                                # Remove unsafe characters for filenames
                                episode_title = re.sub(r'[\\/*?:|]', "_", episode_title)
                            fh.write(f'\t\t<sub-title lang="en">{episode_title}</sub-title>\n')

                        # Description logic
                        description_written = False

                        # Try enhanced descriptions first if enabled
                        if use_extended_desc and need_extended_download:
                            try:
                                enhanced_desc = self._add_enhanced_description(episode_data)
                                if enhanced_desc and str(enhanced_desc).strip():
                                    basic_desc = episode_data.get('epdesc')
                                    basic_desc_str = str(basic_desc).strip() if basic_desc else ''
                                    enhanced_desc_str = str(enhanced_desc).strip()

                                    if (enhanced_desc_str != basic_desc_str or
                                        episode_data.get('epseriesdesc')):  # Has extended data
                                        fh.write(f'\t\t<desc lang="en">{HtmlUtils.conv_html(enhanced_desc)}</desc>\n')
                                        enhanced_desc_count += 1
                                        description_written = True
                            except Exception as e:
                                logging.warning('Error generating enhanced description for episode %s: %s',
                                              episode_key, str(e))

                        # Fallback to basic description
                        if not description_written:
                            basic_desc = episode_data.get('epdesc')
                            if basic_desc and str(basic_desc).strip():
                                fh.write(f'\t\t<desc lang="en">{HtmlUtils.conv_html(basic_desc)}</desc>\n')
                                basic_desc_count += 1
                                description_written = True

                        # Track missing descriptions
                        if not description_written:
                            missing_desc_count += 1
                            program_key = f"{episode_data.get('epshow', 'Unknown')} - {episode_data.get('eptitle', 'None')}"

                            if program_key in missing_desc_programs:
                                missing_desc_programs[program_key] += 1
                            else:
                                missing_desc_programs[program_key] = 1
                                logging.debug('No description available for: %s', program_key)

                        # Length
                        if episode_data.get('eplength'):
                            fh.write(f'\t\t<length units="minutes">{episode_data["eplength"]}</length>\n')

                        # Episode numbering
                        if episode_data.get('epsn') and episode_data.get('epen'):
                            season = str(episode_data['epsn']).zfill(2)
                            episode = str(episode_data['epen']).zfill(2)
                            fh.write(f'\t\t<episode-num system="onscreen">S{season}E{episode}</episode-num>\n')

                            # XMLTV numbering (zero-based)
                            season_xmltv = int(episode_data['epsn']) - 1
                            episode_xmltv = int(episode_data['epen']) - 1
                            fh.write(f'\t\t<episode-num system="xmltv_ns">{season_xmltv}.{episode_xmltv}.</episode-num>\n')

                        # Date
                        if episode_data.get('epyear'):
                            fh.write(f'\t\t<date>{episode_data["epyear"]}</date>\n')

                        # Icons
                        self._write_program_icons(fh, episode_data, ep_icon, episode_key)

                        # Previously shown
                        if not self._is_new_or_live(episode_data):
                            fh.write('\t\t<previously-shown')
                            if episode_data.get('epoad') and int(episode_data['epoad']) > 0:
                                orig_time = TimeUtils.conv_time(float(episode_data['epoad']))
                                fh.write(f' start="{orig_time} {tz_offset}"')
                            fh.write(' />\n')

                        # Subtitles
                        if episode_data.get('eptags') and 'CC' in episode_data['eptags']:
                            fh.write('\t\t<subtitles type="teletext" />\n')

                        # Program flags
                        self._write_program_flags(fh, episode_data)

                        # Rating
                        if episode_data.get('eprating'):
                            fh.write(f'\t\t<rating>\n\t\t\t<value>{episode_data["eprating"]}</value>\n\t\t</rating>\n')

                        # Star rating
                        if episode_data.get('epstar'):
                            fh.write(f'\t\t<star-rating>\n\t\t\t<value>{episode_data["epstar"]}/4</value>\n\t\t</star-rating>\n')

                        # Credits
                        self._write_credits(fh, episode_data)

                        # Categories/Genres
                        self._write_categories(fh, episode_data, ep_genre)

                        fh.write('\t</programme>\n')
                        self.episode_count += 1

                    except Exception as e:
                        logging.exception('Error processing episode %s: %s', episode_key, str(e))

            # Log statistics
            logging.info('Description statistics: Episodes=%d, Basic_desc=%d, Enhanced_desc=%d',
                        self.episode_count, basic_desc_count, enhanced_desc_count)

            # Report missing descriptions
            if missing_desc_count > 0:
                logging.info('Missing descriptions: %d episodes from %d unique programs',
                           missing_desc_count, len(missing_desc_programs))

        except Exception as e:
            logging.exception('Exception in _print_episodes: %s', str(e))

    def _add_enhanced_description(self, episode_data: Dict) -> Optional[str]:
        """Create enhanced description using intelligent default formatting"""
        try:
            # Priority 1: Use extended series description if available
            extended_desc = episode_data.get('epseriesdesc')
            if extended_desc and str(extended_desc).strip():
                extended_desc = str(extended_desc).strip()
            else:
                extended_desc = ''

            # Priority 2: Use basic episode description
            guide_desc = episode_data.get('epdesc')
            if guide_desc and str(guide_desc).strip():
                guide_desc = str(guide_desc).strip()
            else:
                guide_desc = ''

            # Choose primary description
            if extended_desc and len(extended_desc) > len(guide_desc):
                base_desc = extended_desc
                logging.debug('Using extended series description for %s', episode_data.get('epshow', 'Unknown'))
            elif guide_desc:
                base_desc = guide_desc
            else:
                return None

            # Add additional info intelligently
            additional_info = []

            # Add year for movies/shows
            if episode_data.get('epyear') and str(episode_data['epyear']) != '0':
                additional_info.append(f"({episode_data['epyear']})")

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
                    additional_info.append(f"Premiered: {premiere_date}")
                except (ValueError, TypeError, OSError):
                    pass

            # Add rating if available
            if episode_data.get('eprating') and str(episode_data['eprating']).strip():
                additional_info.append(f"Rated: {episode_data['eprating']}")

            # Add flags
            flags = []
            if episode_data.get('epflag') and isinstance(episode_data['epflag'], (list, tuple)):
                if 'New' in episode_data['epflag']:
                    flags.append('NEW')
                if 'Live' in episode_data['epflag']:
                    flags.append('LIVE')
                if 'Premiere' in episode_data['epflag']:
                    flags.append('PREMIERE')
                if 'Finale' in episode_data['epflag']:
                    flags.append('FINALE')

            if episode_data.get('eptags') and isinstance(episode_data['eptags'], (list, tuple)):
                if 'CC' in episode_data['eptags']:
                    flags.append('CC')
                if 'HD' in episode_data['eptags']:
                    flags.append('HD')

            if flags:
                additional_info.append(' '.join(flags))

            # Combine everything intelligently
            if additional_info:
                info_str = ' | '.join(additional_info)
                enhanced_description = f"{base_desc} • {info_str}"

                # Only return enhanced if it's meaningfully different
                if enhanced_description != base_desc:
                    return enhanced_description

            return base_desc if base_desc else None

        except Exception as e:
            logging.warning('Error creating enhanced description for episode %s: %s',
                          episode_data.get('epid', 'unknown'), str(e))
            # Fallback to basic description
            try:
                basic_desc = episode_data.get('epdesc')
                if basic_desc and str(basic_desc).strip():
                    return str(basic_desc).strip()
            except:
                pass
            return None

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

    def _write_program_flags(self, fh, episode_data: Dict):
        """Write program flags (new, live, premiere, etc.)"""
        flags = episode_data.get('epflag', [])
        if isinstance(flags, (list, tuple)):
            if 'Finale' in flags:
                fh.write('\t\t<last-chance />\n')
            if 'Live' in flags:
                fh.write('\t\t<live />\n')
            if 'New' in flags:
                fh.write('\t\t<new />\n')
            if 'Premiere' in flags:
                fh.write('\t\t<premiere />\n')

    def _write_credits(self, fh, episode_data: Dict):
        """Write cast and crew credits"""
        credits = episode_data.get('epcredits')
        if credits and isinstance(credits, list):
            fh.write('\t\t<credits>\n')
            for credit in credits:
                if isinstance(credit, dict):
                    role = credit.get('role', '').lower()
                    name = credit.get('name', '')
                    character = credit.get('characterName', '')
                    asset_id = credit.get('assetId', '')

                    if role and name:
                        if asset_id:
                            fh.write(f'\t\t\t<{role} role="{HtmlUtils.conv_html(character)}" src="https://zap2it.tmsimg.com/assets/{asset_id}.jpg">{HtmlUtils.conv_html(name)}</{role}>\n')
                        else:
                            fh.write(f'\t\t\t<{role} role="{HtmlUtils.conv_html(character)}">{HtmlUtils.conv_html(name)}</{role}>\n')
            fh.write('\t\t</credits>\n')

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
