#!/usr/bin/env python3
"""
Module for parsing Gracenote data (stations and episodes)
"""
import json
import logging
import re
import calendar
import time


def fix_icon_url(icon_data):
    """
    Fix and format icon URL

    Args:
        icon_data: Icon data from API

    Returns:
        str: Complete icon URL or empty string
    """
    if not icon_data:
        return ""

    # If it's already a complete URL, return it
    if isinstance(icon_data, str):
        if icon_data.startswith('http'):
            return icon_data.split('?')[0]  # Remove query parameters
        elif icon_data.startswith('//'):
            return f"http:{icon_data}".split('?')[0]
        elif '/' in icon_data:
            # Probably a relative path
            return f"http://zap2it.tmsimg.com{icon_data}".split('?')[0]

    # If it's a dictionary with icon information
    if isinstance(icon_data, dict):
        # Look for different possible fields
        url = None
        for field in ['url', 'src', 'href', 'link']:
            if field in icon_data:
                url = icon_data[field]
                break

        if url:
            if url.startswith('http'):
                return url.split('?')[0]
            elif url.startswith('//'):
                return f"http:{url}".split('?')[0]
            elif '/' in url:
                return f"http://zap2it.tmsimg.com{url}".split('?')[0]

    # If it's just an image ID, build the URL
    if isinstance(icon_data, str) and not '/' in icon_data:
        # Typical format: p21805903_b_v13_ab -> build complete URL
        # Try different Gracenote/TMS URL formats
        base_urls = [
            "http://zap2it.tmsimg.com/assets/",
            "http://zap2it.tmsimg.com/h3/NowShowing/",
            "http://image.tmdb.org/t/p/w185/",
            "http://tvlistings.gracenote.com/static/"
        ]

        # For IDs starting with 'p' (programs)
        if icon_data.startswith('p'):
            return f"http://zap2it.tmsimg.com/assets/{icon_data}.jpg"
        # For IDs starting with 's' (stations/channels)
        elif icon_data.startswith('s'):
            return f"http://zap2it.tmsimg.com/h3/NowShowing/{icon_data}_ll_h15_ab.png"
        else:
            # Generic format
            return f"http://zap2it.tmsimg.com/assets/{icon_data}.jpg"

    return ""


def parseStations(content, config, schedule, tvhMatchDict):
    """
    Parse stations from JSON content

    Args:
        content: JSON content from Gracenote API
        config: Configuration dictionary
        schedule: Global schedule dictionary to populate
        tvhMatchDict: TVHeadend channel mapping dictionary

    Returns:
        int: Number of processed stations
    """
    try:
        ch_guide = json.loads(content)
        logging.info('Parsing stations from API response')

        if 'channels' not in ch_guide:
            logging.warning('No "channels" key found in API response')
            return 0

        channels_list = ch_guide['channels']
        logging.info('Found %d channels in API response', len(channels_list))

        processed_count = 0

        for station in channels_list:
            skey = station.get('channelId')
            if not skey:
                continue

            # Configuration-based filtering
            should_process = False

            # If we have an explicit station list in config
            if config['stationList'] is not None and config['stationList'].strip():
                should_process = skey in config['stationList'].split(',')
            # If we use TVHeadend filter
            elif config.get('use_tvh_filter', False):
                chnumStart = str(station.get('channelNo', ''))
                chSign = station.get('callSign')

                # Create channel number - simplified logic
                if '.' not in chnumStart and chSign is not None:
                    chsub = re.search(r'(\d+)$', chSign)
                    if chsub is not None:
                        channel_num = chnumStart + '.' + chsub.group(0)
                    else:
                        channel_num = chnumStart + '.1'
                else:
                    channel_num = chnumStart

                # Check if this channel exists in TVHeadend
                should_process = channel_num in config.get('tvh_channels', [])

                if should_process:
                    logging.debug('Channel %s (%s) matches TVHeadend channel %s', skey, chSign, channel_num)
            else:
                # No filter - process all stations
                should_process = True

            if should_process:
                schedule[skey] = {}
                chSign = station.get('callSign')
                chName = station.get('affiliateName')
                schedule[skey]['chfcc'] = chSign
                schedule[skey]['chnam'] = chName

                # Icon correction - look in multiple possible fields
                icon_url = ""

                # Look in different icon fields
                for icon_field in ['thumbnail', 'logo', 'icon', 'image', 'logoURL']:
                    if icon_field in station and station[icon_field]:
                        icon_url = fix_icon_url(station[icon_field])
                        if icon_url:
                            logging.debug('Found icon for %s in field %s: %s', skey, icon_field, icon_url)
                            break

                # If no icon found, try to build from station ID
                if not icon_url and skey:
                    icon_url = fix_icon_url(skey)
                    if icon_url:
                        logging.debug('Generated icon URL for %s: %s', skey, icon_url)

                schedule[skey]['chicon'] = icon_url

                chnumStart = station.get('channelNo')

                # Channel number simplification
                if '.' not in str(chnumStart) and chSign is not None:
                    chsub = re.search(r'(\d+)$', chSign)
                    if chsub is not None:
                        chnumUpdate = str(chnumStart) + '.' + chsub.group(0)
                    else:
                        chnumUpdate = str(chnumStart) + '.1'
                else:
                    chnumUpdate = str(chnumStart)

                schedule[skey]['chnum'] = chnumUpdate

                # Add TVHeadend name if available
                if config['tvhmatch'] == 'true' and '.' in chnumUpdate:
                    if chnumUpdate in tvhMatchDict:
                        schedule[skey]['chtvh'] = tvhMatchDict[chnumUpdate]
                    else:
                        schedule[skey]['chtvh'] = None

                processed_count += 1
                logging.debug('Processed station %s: num=%s, icon=%s',
                             skey, chnumUpdate, schedule[skey]['chicon'][:50] + '...' if schedule[skey]['chicon'] else 'None')

        logging.info('Successfully parsed %d/%d stations (filtered by %s)',
                    processed_count, len(channels_list),
                    'explicit list' if (config['stationList'] and config['stationList'].strip())
                    else 'TVHeadend' if config.get('use_tvh_filter')
                    else 'none (all stations)')

        return processed_count

    except Exception as e:
        logging.exception('Exception: parseStations')
        return 0


def parseEpisodes(content, config, schedule):
    """
    Parse episodes from JSON content

    Args:
        content: JSON content from Gracenote API
        config: Configuration dictionary
        schedule: Global schedule dictionary to populate

    Returns:
        str: "Safe" or "Unsafe" depending on TBA content found
    """
    CheckTBA = "Safe"
    try:
        ch_guide = json.loads(content)
        logging.info('Parsing episodes from API response')

        # Check if response contains channels
        if 'channels' not in ch_guide:
            logging.warning('No "channels" key found in API response for episodes')
            return CheckTBA

        for station in ch_guide['channels']:
            skey = station.get('channelId')
            if not skey:
                continue

            # Check if we should process this station
            if config['stationList'] and config['stationList'].strip():
                if skey not in config['stationList'].split(','):
                    continue

            # Make sure station exists in schedule
            if skey not in schedule:
                continue

            episodes = station.get('events', [])
            logging.debug('Processing %d episodes for station %s', len(episodes), skey)

            for episode in episodes:
                try:
                    start_time = episode.get('startTime')
                    if not start_time:
                        continue

                    epkey = str(calendar.timegm(time.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ')))
                    schedule[skey][epkey] = {}

                    program = episode.get('program', {})
                    schedule[skey][epkey]['epid'] = program.get('tmsId')
                    schedule[skey][epkey]['epstart'] = epkey

                    end_time = episode.get('endTime')
                    if end_time:
                        schedule[skey][epkey]['epend'] = str(calendar.timegm(time.strptime(end_time, '%Y-%m-%dT%H:%M:%SZ')))
                    else:
                        schedule[skey][epkey]['epend'] = epkey

                    schedule[skey][epkey]['eplength'] = episode.get('duration')
                    schedule[skey][epkey]['epshow'] = program.get('title')
                    schedule[skey][epkey]['eptitle'] = program.get('episodeTitle')
                    schedule[skey][epkey]['epdesc'] = program.get('shortDesc')
                    schedule[skey][epkey]['epyear'] = program.get('releaseYear')
                    schedule[skey][epkey]['eprating'] = episode.get('rating')
                    schedule[skey][epkey]['epflag'] = episode.get('flag', [])
                    schedule[skey][epkey]['eptags'] = episode.get('tags', [])
                    schedule[skey][epkey]['epsn'] = program.get('season')
                    schedule[skey][epkey]['epen'] = program.get('episode')

                    # Episode icon correction
                    episode_thumbnail = episode.get('thumbnail')
                    if episode_thumbnail:
                        schedule[skey][epkey]['epthumb'] = fix_icon_url(episode_thumbnail)
                    else:
                        schedule[skey][epkey]['epthumb'] = None

                    schedule[skey][epkey]['epoad'] = None
                    schedule[skey][epkey]['epstar'] = None
                    schedule[skey][epkey]['epfilter'] = episode.get('filter', [])

                    # Genre management
                    genres = program.get('genres', [])
                    if genres:
                        schedule[skey][epkey]['epgenres'] = genres
                    else:
                        schedule[skey][epkey]['epgenres'] = None

                    # Credits management
                    credits = program.get('credits', {})
                    if credits:
                        schedule[skey][epkey]['epcredits'] = credits
                    else:
                        schedule[skey][epkey]['epcredits'] = None

                    schedule[skey][epkey]['epxdesc'] = program.get('longDesc')
                    schedule[skey][epkey]['epseries'] = episode.get('seriesId')

                    # Episode image (different from thumbnail)
                    episode_image = program.get('image')
                    if episode_image:
                        schedule[skey][epkey]['epimage'] = fix_icon_url(episode_image)
                    else:
                        schedule[skey][epkey]['epimage'] = None

                    schedule[skey][epkey]['epfan'] = None

                    # Check for TBA content
                    ep_show = schedule[skey][epkey]['epshow']
                    ep_title = schedule[skey][epkey]['eptitle']

                    if ep_show and "TBA" in ep_show:
                        CheckTBA = "Unsafe"
                    elif ep_title and "TBA" in ep_title:
                        CheckTBA = "Unsafe"

                except Exception as e:
                    logging.warning('Error parsing episode in station %s: %s', skey, str(e))
                    continue

    except Exception as e:
        logging.exception('Exception: parseEpisodes')

    return CheckTBA


def validateChannelNumber(chnumStart, chSign):
    """
    Create and validate channel number based on call sign

    Args:
        chnumStart: Starting channel number from API
        chSign: Channel call sign

    Returns:
        str: Formatted channel number
    """
    if '.' not in str(chnumStart) and chSign is not None:
        chsub = re.search(r'(\d+)$', chSign)
        if chsub is not None:
            return str(chnumStart) + '.' + chsub.group(0)
        else:
            return str(chnumStart) + '.1'
    else:
        return str(chnumStart)


def shouldProcessStation(skey, station, config):
    """
    Determine if a station should be processed based on configuration

    Args:
        skey: Station key (channelId)
        station: Station data from API
        config: Configuration dictionary

    Returns:
        tuple: (should_process: bool, channel_number: str)
    """
    should_process = False
    channel_number = ""

    # If we have an explicit station list in config
    if config['stationList'] is not None and config['stationList'].strip():
        should_process = skey in config['stationList'].split(',')
    # If we use TVHeadend filter
    elif config.get('use_tvh_filter', False):
        chnumStart = str(station.get('channelNo', ''))
        chSign = station.get('callSign')

        channel_number = validateChannelNumber(chnumStart, chSign)
        should_process = channel_number in config.get('tvh_channels', [])

        if should_process:
            logging.debug('Channel %s (%s) matches TVHeadend channel %s', skey, chSign, channel_number)
    else:
        # No filter - process all stations
        should_process = True

    return should_process, channel_number


def debug_station_icons(schedule):
    """
    Debug function to check station icons

    Args:
        schedule: Schedule dictionary
    """
    logging.info('=== DEBUG: Station Icons ===')
    for station_id, station_data in schedule.items():
        if not station_id.startswith('ch'):  # Skip episode data
            continue
        icon = station_data.get('chicon', 'No icon')
        chfcc = station_data.get('chfcc', 'Unknown')
        logging.info('Station %s (%s): %s', station_id, chfcc, icon)
    logging.info('=== END DEBUG ===')


def debug_episode_icons(schedule, station_limit=2, episode_limit=3):
    """
    Debug function to check episode icons

    Args:
        schedule: Schedule dictionary
        station_limit: Number of stations to check
        episode_limit: Number of episodes per station
    """
    logging.info('=== DEBUG: Episode Icons ===')
    station_count = 0

    for station_id, station_data in schedule.items():
        if station_count >= station_limit:
            break

        episode_count = 0
        chfcc = station_data.get('chfcc', 'Unknown')
        logging.info('Station %s (%s):', station_id, chfcc)

        for episode_key, episode_data in station_data.items():
            if episode_key.startswith('ch') or episode_count >= episode_limit:
                continue

            epshow = episode_data.get('epshow', 'Unknown')
            epthumb = episode_data.get('epthumb', 'No thumbnail')
            epimage = episode_data.get('epimage', 'No image')

            logging.info('  Episode %s: thumb=%s, image=%s', epshow[:30], epthumb, epimage)
            episode_count += 1

        station_count += 1

    logging.info('=== END DEBUG ===')
