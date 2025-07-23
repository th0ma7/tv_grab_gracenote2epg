#!/usr/bin/env python3
"""
Utility functions module for gracenote2epg
"""
import time
import gzip
import os
import logging

def convTime(t):
    """Convert timestamp to XMLTV format"""
    return time.strftime("%Y%m%d%H%M%S", time.localtime(int(t)))

def convHTML(data):
    """Escape HTML characters"""
    if not data:
        return ""
    data = str(data)
    data = data.replace('&', '&amp;')
    data = data.replace('"', '&quot;')
    data = data.replace("'", '&apos;')
    data = data.replace('<', '&lt;')
    data = data.replace('>', '&gt;')
    return data

def savepage(fn, data, cache_dir):
    """Save page - handles already compressed content"""
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
    fileDir = os.path.join(cache_dir, fn)

    # Check if data is already gzipped (starts with magic bytes)
    if isinstance(data, bytes) and len(data) >= 2 and data[:2] == b'\x1f\x8b':
        # Content already compressed, save as-is
        with open(fileDir, "wb") as f:
            f.write(data)
    else:
        # Uncompressed content, compress it
        with gzip.open(fileDir, "wb") as f:
            if isinstance(data, str):
                f.write(data.encode('utf-8'))
            else:
                f.write(data)

def deleteOldCache(gridtimeStart, redays, cache_dir):
    """Remove old cache files"""
    logging.info('Checking for old cache files...')
    try:
        if os.path.exists(cache_dir):
            entries = os.listdir(cache_dir)
            for entry in entries:
                oldfile = entry.split('.')[0]
                if oldfile.isdigit():
                    fn = os.path.join(cache_dir, entry)
                    if (int(oldfile)) < (gridtimeStart + (int(redays) * 86400)):
                        try:
                            os.remove(fn)
                            logging.info('Deleting old cache: %s', entry)
                        except OSError as e:
                            logging.warning('Error Deleting: %s - %s.' % (e.filename, e.strerror))
    except Exception as e:
        logging.exception('Exception: deleteOldCache - %s', str(e))

def deleteOldShowCache(showList, cache_dir):
    """Remove old show cache files"""
    logging.info('Checking for old show cache files...')
    try:
        if os.path.exists(cache_dir):
            entries = os.listdir(cache_dir)
            for entry in entries:
                oldfile = entry.split('.')[0]
                if not oldfile.isdigit():
                    fn = os.path.join(cache_dir, entry)
                    if oldfile not in showList:
                        try:
                            os.remove(fn)
                            logging.info('Deleting old show cache: %s', entry)
                        except OSError as e:
                            logging.warning('Error Deleting: %s - %s.' % (e.filename, e.strerror))
    except Exception as e:
        logging.exception('Exception: deleteOldshowCache - %s', str(e))

def genShowList(schedule):
    """Generate show list"""
    showList = []
    for station in schedule:
        sdict = schedule[station]
        for episode in sdict:
            if not episode.startswith("ch"):
                edict = sdict[episode]
                series_id = edict.get('epseries')
                if series_id:
                    showList.append(series_id)
    return showList
