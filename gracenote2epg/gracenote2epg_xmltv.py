#!/usr/bin/env python3
"""
XMLTV generation module
"""
import os
import time
import codecs
import logging
from collections import OrderedDict
from typing import Dict, Any, Tuple

from .gracenote2epg_utils import convTime, convHTML


class XMLTVGenerator:
    """
    XMLTV file generator
    """

    def __init__(self, config: dict):
        """
        Initialize XMLTV generator

        Args:
            config: gracenote2epg configuration
        """
        self.config = config
        self.station_count = 0
        self.episode_count = 0
        self.encoding = 'utf-8'

    def generate_xmltv_file(self, schedule: Dict[str, Any]) -> Tuple[int, int]:
        """
        Generate complete XMLTV file

        Args:
            schedule: Guide data dictionary

        Returns:
            Tuple (station count, episode count)
        """
        try:
            output_file = os.path.join(self.config['userdata'],
                                     os.environ.get('XMLTV', 'xmltv.xml'))

            logging.info('Creating xmltv.xml file: %s', output_file)

            with codecs.open(output_file, 'w', encoding=self.encoding) as fh:
                self._write_header(fh)
                self._write_stations(fh, schedule)
                self._write_episodes(fh, schedule)
                self._write_footer(fh)

            logging.info('XMLTV file created successfully')
            logging.info('%s Stations and %s Episodes written to xmltv.xml file.',
                        str(self.station_count), str(self.episode_count))

            return self.station_count, self.episode_count

        except Exception as e:
            logging.exception('Exception: generate_xmltv_file')
            return 0, 0

    def _write_header(self, fh):
        """
        Write XMLTV file header

        Args:
            fh: File handle
        """
        logging.info('Writing XMLTV header...')
        fh.write(f"<?xml version=\"1.0\" encoding=\"{self.encoding}\"?>\n")
        fh.write("<!DOCTYPE tv SYSTEM \"xmltv.dtd\">\n")
        fh.write("<tv source-info-url=\"http://tvschedule.gracenote.com/\" "
                "source-info-name=\"gracenote.com\">\n")

    def _write_footer(self, fh):
        """
        Write XMLTV file footer

        Args:
            fh: File handle
        """
        fh.write("</tv>\n")

    def _write_stations(self, fh, schedule: Dict[str, Any]):
        """
        Write stations to XMLTV file

        Args:
            fh: File handle
            schedule: Guide data dictionary
        """
        self.station_count = 0
        try:
            logging.info('Writing Stations to xmltv.xml file...')

            # Sort stations by channel number
            try:
                schedule_sort = OrderedDict(sorted(iter(schedule.items()),
                                                 key=lambda x: int(x[1]['chnum'])))
            except:
                schedule_sort = OrderedDict(sorted(iter(schedule.items()),
                                                 key=lambda x: x[1]['chfcc']))

            for station in schedule_sort:
                self._write_single_station(fh, station, schedule_sort[station])
                self.station_count += 1

        except Exception as e:
            logging.exception('Exception: _write_stations')

    def _write_single_station(self, fh, station_id: str, station_data: Dict[str, Any]):
        """
        Write single station to XMLTV file

        Args:
            fh: File handle
            station_id: Station ID
            station_data: Station data
        """
        fh.write(f'\t<channel id="{station_id}.gracenote2epg">\n')

        # TVHeadend name if available
        if 'chtvh' in station_data and station_data['chtvh'] is not None:
            xchtvh = convHTML(station_data['chtvh'])
            fh.write(f'\t\t<display-name>{xchtvh}</display-name>\n')

        # Main channel information
        if 'chnum' in station_data and 'chfcc' in station_data:
            xchnum = station_data['chnum']
            xchfcc = station_data['chfcc']
            xchnam = station_data['chnam']

            fh.write(f'\t\t<display-name>{xchnum} {convHTML(xchfcc)}</display-name>\n')

            if xchnam != "INDEPENDENT":
                fh.write(f'\t\t<display-name>{convHTML(xchnam)}</display-name>\n')

            fh.write(f'\t\t<display-name>{convHTML(xchfcc)}</display-name>\n')
            fh.write(f'\t\t<display-name>{xchnum}</display-name>\n')

        elif 'chfcc' in station_data:
            xchfcc = station_data['chfcc']
            fh.write(f'\t\t<display-name>{convHTML(xchfcc)}</display-name>\n')

        elif 'chnum' in station_data:
            xchnum = station_data['chnum']
            fh.write(f'\t\t<display-name>{xchnum}</display-name>\n')

        # Channel icon
        if 'chicon' in station_data and station_data['chicon']:
            icon_url = station_data['chicon']
            # Ensure URL starts with http
            if not icon_url.startswith('http'):
                icon_url = f"http:{icon_url}"
            fh.write(f"\t\t<icon src=\"{icon_url}\" />\n")

        fh.write("\t</channel>\n")

    def _write_episodes(self, fh, schedule: Dict[str, Any]):
        """
        Write episodes to XMLTV file

        Args:
            fh: File handle
            schedule: Guide data dictionary
        """
        self.episode_count = 0
        try:
            logging.info('Writing Episodes to xmltv.xml file...')

            if self.config['xdesc'] == 'true':
                logging.info('Appending Xdetails to description for xmltv.xml file...')

            for station in schedule:
                self._write_station_episodes(fh, station, schedule[station])

        except Exception as e:
            logging.exception('Exception: _write_episodes')

    def _write_station_episodes(self, fh, station_id: str, station_data: Dict[str, Any]):
        """
        Write station episodes to XMLTV file

        Args:
            fh: File handle
            station_id: Station ID
            station_data: Station data
        """
        lang = 'en'

        for episode_key in station_data:
            if not episode_key.startswith("ch"):
                try:
                    episode_data = station_data[episode_key]

                    if 'epstart' in episode_data:
                        self._write_single_episode(fh, station_id, episode_data, lang)
                        self.episode_count += 1

                except Exception as e:
                    logging.warning('No data for episode %s: %s', episode_key, str(e))

    def _write_single_episode(self, fh, station_id: str, episode_data: Dict[str, Any], lang: str):
        """
        Write single episode to XMLTV file

        Args:
            fh: File handle
            station_id: Station ID
            episode_data: Episode data
            lang: Language code
        """
        # Calculate start and stop times
        start_time = convTime(episode_data['epstart'])
        stop_time = convTime(episode_data['epend'])

        # Calculate timezone offset
        is_dst = time.daylight and time.localtime().tm_isdst > 0
        tz_offset = "%.2d%.2d" % (- (time.altzone if is_dst else time.timezone)/3600, 0)

        # Program start
        fh.write(f'\t<programme start="{start_time} {tz_offset}" '
                f'stop="{stop_time} {tz_offset}" '
                f'channel="{station_id}.gracenote2epg">\n')

        # Program ID
        dd_progid = episode_data['epid']
        if dd_progid:
            fh.write(f'\t\t<episode-num system="dd_progid">'
                    f'{dd_progid[:-4]}.{dd_progid[-4:]}</episode-num>\n')

        # Program title
        if episode_data['epshow'] is not None:
            fh.write(f'\t\t<title lang="{lang}">'
                    f'{convHTML(episode_data["epshow"])}</title>\n')

        # Episode title
        if episode_data.get('eptitle') is not None:
            fh.write(f'\t\t<sub-title lang="{lang}">'
                    f'{convHTML(episode_data["eptitle"])}</sub-title>\n')

        # Description
        if episode_data['epdesc'] is not None:
            description = self._build_description(episode_data)
            fh.write(f'\t\t<desc lang="{lang}">{convHTML(description)}</desc>\n')

        # Duration
        if episode_data['eplength'] is not None:
            fh.write(f'\t\t<length units="minutes">{str(episode_data["eplength"])}</length>\n')

        # Season and episode numbers
        if episode_data['epsn'] is not None and episode_data['epen'] is not None:
            season_num = str(episode_data['epsn']).zfill(2)
            episode_num = str(episode_data['epen']).zfill(2)

            fh.write(f"\t\t<episode-num system=\"onscreen\">S{season_num}E{episode_num}</episode-num>\n")
            fh.write(f"\t\t<episode-num system=\"xmltv_ns\">"
                    f"{int(episode_data['epsn'])-1}.{int(episode_data['epen'])-1}.</episode-num>\n")

        # Year
        if episode_data['epyear'] is not None:
            fh.write(f'\t\t<date>{str(episode_data["epyear"])}</date>\n')

        # Rating
        if episode_data['eprating'] is not None:
            fh.write(f'\t\t<rating>\n\t\t\t<value>{str(episode_data["eprating"])}</value>\n\t\t</rating>\n')

        # Categories/Genres
        if episode_data.get('epgenres') is not None:
            for genre in episode_data['epgenres']:
                fh.write(f'\t\t<category lang="{lang}">{convHTML(genre)}</category>\n')

        # Credits
        if episode_data.get('epcredits') is not None:
            self._write_credits(fh, episode_data['epcredits'])

        # Image/Icon
        if episode_data.get('epimage') is not None:
            fh.write(f'\t\t<icon src="{episode_data["epimage"]}" />\n')
        elif episode_data.get('epthumb') is not None:
            fh.write(f'\t\t<icon src="{episode_data["epthumb"]}" />\n')

        # End program
        fh.write("\t</programme>\n")

    def _build_description(self, episode_data: Dict[str, Any]) -> str:
        """
        Build episode description based on configuration

        Args:
            episode_data: Episode data

        Returns:
            str: Formatted description
        """
        description = episode_data['epdesc'] or ""

        # If xdesc is enabled, add extra details
        if self.config.get('xdesc') == 'true' and episode_data.get('epxdesc'):
            if description:
                description += "\n\n"
            description += episode_data['epxdesc']

        return description

    def _write_credits(self, fh, credits: Dict[str, Any]):
        """
        Write credits to XMLTV file

        Args:
            fh: File handle
            credits: Credits dictionary
        """
        if not credits:
            return

        fh.write('\t\t<credits>\n')

        # Actors
        if 'actors' in credits:
            for actor in credits['actors']:
                if isinstance(actor, dict):
                    name = actor.get('name', '')
                    role = actor.get('role', '')
                    if name:
                        if role:
                            fh.write(f'\t\t\t<actor role="{convHTML(role)}">{convHTML(name)}</actor>\n')
                        else:
                            fh.write(f'\t\t\t<actor>{convHTML(name)}</actor>\n')
                else:
                    fh.write(f'\t\t\t<actor>{convHTML(str(actor))}</actor>\n')

        # Directors
        if 'directors' in credits:
            for director in credits['directors']:
                fh.write(f'\t\t\t<director>{convHTML(str(director))}</director>\n')

        # Producers
        if 'producers' in credits:
            for producer in credits['producers']:
                fh.write(f'\t\t\t<producer>{convHTML(str(producer))}</producer>\n')

        # Writers
        if 'writers' in credits:
            for writer in credits['writers']:
                fh.write(f'\t\t\t<writer>{convHTML(str(writer))}</writer>\n')

        fh.write('\t\t</credits>\n')

    def get_stats(self) -> Tuple[int, int]:
        """
        Return generation statistics

        Returns:
            Tuple (station count, episode count)
        """
        return self.station_count, self.episode_count

    def reset_stats(self):
        """
        Reset statistics
        """
        self.station_count = 0
        self.episode_count = 0


class XMLTVValidator:
    """
    Validator for XMLTV files
    """

    @staticmethod
    def validate_xmltv_file(file_path: str) -> Tuple[bool, str]:
        """
        Validate XMLTV file

        Args:
            file_path: XMLTV file path

        Returns:
            Tuple (valid: bool, message: str)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File does not exist: {file_path}"

            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False, "File is empty"

            # Check basic XML format
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if not first_line.startswith('<?xml'):
                    return False, "File does not start with XML declaration"

            logging.info(f"XMLTV file validation passed: {file_path} ({file_size} bytes)")
            return True, f"Valid XMLTV file ({file_size} bytes)"

        except Exception as e:
            return False, f"Validation error: {str(e)}"


def create_xmltv_generator(config: dict) -> XMLTVGenerator:
    """
    Factory function to create an XMLTV generator

    Args:
        config: gracenote2epg configuration

    Returns:
        XMLTVGenerator instance
    """
    return XMLTVGenerator(config)


def generate_xmltv_from_schedule(schedule: Dict[str, Any], config: dict) -> Tuple[int, int]:
    """
    Utility function to generate XMLTV file from schedule

    Args:
        schedule: Guide data dictionary
        config: gracenote2epg configuration

    Returns:
        Tuple (station count, episode count)
    """
    generator = create_xmltv_generator(config)
    return generator.generate_xmltv_file(schedule)
