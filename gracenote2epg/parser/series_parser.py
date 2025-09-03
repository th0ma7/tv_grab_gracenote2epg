"""
Series details parser for gracenote2epg
"""

import logging
import calendar
import time
import re
from typing import Dict, Optional


class SeriesParser:
    """Parses extended series details"""
    
    def parse_series_details(self, episode_data: Dict, series_details: Dict, 
                            series_id: str) -> bool:
        """
        Parse and apply series details to episode
        
        Args:
            episode_data: Episode data to update
            series_details: Series details from API
            series_id: Series ID
            
        Returns:
            bool: True if successful
        """
        try:
            # Extract extended series description
            series_desc = series_details.get("seriesDescription")
            if series_desc and str(series_desc).strip():
                episode_data["epseriesdesc"] = str(series_desc).strip()
                logging.debug(
                    "Found extended series description for %s: %s",
                    series_id,
                    series_desc[:50] + "..." if len(series_desc) > 50 else series_desc,
                )
            
            # Process images
            episode_data["epimage"] = series_details.get("seriesImage")
            episode_data["epfan"] = series_details.get("backgroundImage")
            
            # Handle genres
            self._parse_genres(episode_data, series_details, series_id)
            
            # Process credits for movies
            if series_id.startswith("MV"):
                self._parse_movie_credits(episode_data, series_details)
            
            # Process upcoming episodes for original air date
            self._parse_original_air_date(episode_data, series_details, series_id)
            
            return True
            
        except Exception as e:
            logging.warning(
                "Error processing series details for %s: %s",
                series_id,
                str(e),
            )
            return False
    
    def _parse_genres(self, episode_data: Dict, series_details: Dict, 
                     series_id: str):
        """Parse and process genres"""
        ep_genres = series_details.get("seriesGenres")
        
        if series_id.startswith("MV"):  # Movie
            ep_genres = "Movie|" + ep_genres if ep_genres else "Movie"
            
        if ep_genres:
            episode_data["epgenres"] = ep_genres.split("|")
    
    def _parse_movie_credits(self, episode_data: Dict, series_details: Dict):
        """Parse credits for movies"""
        overview_tab = series_details.get("overviewTab", {})
        if isinstance(overview_tab, dict):
            episode_data["epcredits"] = overview_tab.get("cast")
    
    def _parse_original_air_date(self, episode_data: Dict, 
                                 series_details: Dict, series_id: str):
        """Parse original air date from upcoming episodes"""
        ep_list = series_details.get("upcomingEpisodeTab", [])
        if not isinstance(ep_list, list):
            return
            
        ep_id = episode_data.get("epid", "")
        
        for airing in ep_list:
            if not isinstance(airing, dict):
                continue
                
            if ep_id.lower() == airing.get("tmsID", "").lower():
                if not series_id.startswith("MV"):  # Not a movie
                    try:
                        orig_date = airing.get("originalAirDate")
                        if orig_date and orig_date != "":
                            # Handle date format
                            ep_oad = re.sub("Z", ":00Z", orig_date)
                            episode_data["epoad"] = str(
                                calendar.timegm(
                                    time.strptime(ep_oad, "%Y-%m-%dT%H:%M:%SZ")
                                )
                            )
                    except Exception:
                        pass
                    
                    # Check for TBA listings
                    self._check_tba_in_airing(airing, series_id)
    
    def _check_tba_in_airing(self, airing: Dict, series_id: str):
        """Check for TBA content in airing data"""
        try:
            tba_check = airing.get("episodeTitle", "")
            if tba_check and "TBA" in tba_check:
                logging.info("  Found TBA listing in %s", series_id)
        except Exception:
            pass
