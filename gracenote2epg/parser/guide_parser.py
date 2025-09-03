"""
Guide data parser for gracenote2epg
"""

import json
import logging
import calendar
import time
from typing import Dict, Optional

class GuideParser:
    """Parses TV guide JSON data"""
    
    def __init__(self, tvh_client=None):
        self.tvh_client = tvh_client
        self.schedule: Dict = {}
        
    def parse_stations(self, content: bytes) -> bool:
        """Parse station information from guide data"""
        try:
            ch_guide = json.loads(content)
            
            for station in ch_guide.get("channels", []):
                station_id = station.get("channelId")
                
                if self._should_process_station(station):
                    self.schedule[station_id] = {}
                    
                    # Extract station info
                    self.schedule[station_id]["chfcc"] = station.get("callSign")
                    self.schedule[station_id]["chnam"] = station.get("affiliateName")
                    
                    # Extract icon URL
                    thumbnail = station.get("thumbnail", "")
                    if thumbnail:
                        self.schedule[station_id]["chicon"] = thumbnail.split("?")[0]
                    else:
                        self.schedule[station_id]["chicon"] = ""
                    
                    # Handle channel number
                    if self.tvh_client:
                        matched_channel = self.tvh_client.get_matched_channel_number(
                            station, use_channel_matching=True
                        )
                        tvh_name = self.tvh_client.get_tvh_channel_name(matched_channel)
                    else:
                        matched_channel = station.get("channelNo", "")
                        tvh_name = None
                    
                    self.schedule[station_id]["chnum"] = matched_channel
                    self.schedule[station_id]["chtvh"] = tvh_name
                    
            return True
            
        except Exception as e:
            logging.exception("Exception in parse_stations: %s", str(e))
            return False
    
    def parse_episodes(self, content: bytes) -> str:
        """Parse episode information from guide data"""
        check_tba = "Safe"
        
        try:
            ch_guide = json.loads(content)
            
            for station in ch_guide.get("channels", []):
                station_id = station.get("channelId")
                
                if self._should_process_station(station):
                    episodes = station.get("events", [])
                    
                    for episode in episodes:
                        episode_data = self._parse_episode(episode)
                        if episode_data:
                            ep_key = episode_data["epstart"]
                            self.schedule[station_id][ep_key] = episode_data
                            
                            # Check for TBA
                            if self._check_tba(episode_data):
                                check_tba = "Unsafe"
                                
        except Exception as e:
            logging.exception("Exception in parse_episodes: %s", str(e))
            
        return check_tba
    
    def _parse_episode(self, episode: Dict) -> Optional[Dict]:
        """Parse individual episode data"""
        # Extract start time
        start_time_str = episode.get("startTime", "")
        if not start_time_str:
            return None
            
        try:
            ep_key = str(
                calendar.timegm(
                    time.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")
                )
            )
        except (ValueError, TypeError):
            return None
        
        # Extract end time
        end_time_str = episode.get("endTime", "")
        ep_end = None
        if end_time_str:
            try:
                ep_end = str(
                    calendar.timegm(
                        time.strptime(end_time_str, "%Y-%m-%dT%H:%M:%SZ")
                    )
                )
            except (ValueError, TypeError):
                pass
        
        # Get program info
        program = episode.get("program", {})
        
        # Get descriptions
        short_desc = program.get("shortDesc") or ""
        long_desc = program.get("longDesc") or ""
        
        # Build episode data
        return {
            "epid": program.get("tmsId"),
            "epstart": ep_key,
            "epend": ep_end,
            "eplength": episode.get("duration"),
            "epshow": program.get("title"),
            "eptitle": program.get("episodeTitle"),
            "epdesc": long_desc if long_desc else short_desc,
            "epyear": program.get("releaseYear"),
            "eprating": episode.get("rating"),
            "epflag": episode.get("flag", []),
            "eptags": episode.get("tags", []),
            "epsn": program.get("season"),
            "epen": program.get("episode"),
            "epthumb": (
                episode.get("thumbnail", "").split("?")[0]
                if episode.get("thumbnail")
                else ""
            ),
            "epoad": None,
            "epstar": None,
            "epfilter": episode.get("filter", []),
            "epgenres": None,
            "epcredits": None,
            "epseries": program.get("seriesId"),
            "epimage": None,
            "epfan": None,
            "epseriesdesc": None,
        }
    
    def _should_process_station(self, station_data: Dict) -> bool:
        """Determine if a station should be processed"""
        if self.tvh_client:
            return self.tvh_client.should_process_station(
                station_data,
                explicit_station_list=None,
                use_tvh_matching=True,
                use_channel_matching=True,
            )
        return True
    
    def _check_tba(self, episode_data: Dict) -> bool:
        """Check if episode contains TBA content"""
        if episode_data.get("epshow") and "TBA" in episode_data["epshow"]:
            return True
        if episode_data.get("eptitle") and "TBA" in episode_data["eptitle"]:
            return True
        return False
    
    def get_schedule(self) -> Dict:
        """Get the parsed schedule"""
        return self.schedule
