# tv_grab_gracenote2epg - TVHeadend XMLTV Grabber
North America (gracenote2epg using tvlistings.gracenote.com)

`tv_grab_gracenote2epg` generates an `xmltv.xml` file for Canada/USA TV lineups by fetching channel lists from TVHeadend and downloading relevant entries from tvlistings.gracenote.com.

gracenote2epg was originally designed to be easily setup in Kodi for use as a grabber for TVHeadend. This is a fork of the original code from edit4ever Python3 branch of script.module.zap2epg based on PR https://github.com/edit4ever/script.module.zap2epg/pull/37 (much thanks for your great original work @edit4ever !!!)

It includes the ability to automatically fetch your channel list from TVH to reduce the amount of data downloaded and speed up the grab. It has an option for downloading extra detail information for programs. (Note: this option will generate an extra http request per episode) It also has an option to append the extra detail information to the description (plot) field, which makes displaying this information in the Kodi EPG easier on many skins.

_Note that gracenote2epg is a proof of concept and is for personal experimentation only. It is not meant to be used in a commercial product and its use is your own responsibility._

## `tv_grab_gracenote2epg` capabilities
gracenote2epg TV guide grabber script provides `baseline` capabilities (ref: http://wiki.xmltv.org/index.php/XmltvCapabilities):

### Standard XMLTV Options:
- `--description`: Show description and exit
- `--version`: Show version number and exit  
- `--capabilities`: Show grabber capabilities and exit
- `--quiet`: Suppress all progress information. When --quiet is used, the grabber shall only print error-messages to stderr.
- `--output FILENAME`: Redirect the xmltv output to the specified file. Otherwise output goes to stdout along with a copy under `epggrab/cache/xmltv.xml`.
- `--days X`: Supply data for X days, limited to 14.
- `--offset X`: Start with data for day today plus X days. The default is 0, today; 1 means start from tomorrow, etc.
- `--config-file FILENAME`: The grabber shall read all configuration data from the specified file. Otherwise uses default under `epggrab/conf/gracenote2epg.xml`

### Extended Options:
- `--zip` or `--postal` or `--code`: Allow can be used to pass US Zip or Canadian Postal code to be used by the grabber.
- `--base-dir DIRECTORY`: Set custom base directory for cache/config/logs (default: ~/gracenote2epg)

### Logging Control Options:
- `--debug`: Enable debug logging (most verbose) - shows DEBUG, INFO, WARNING, ERROR messages
- `--warning`: Enable warning level logging only - shows WARNING, ERROR messages  
- `--silent`: Silent mode - only log errors (ERROR messages only)
- *(default)*: Show INFO, WARNING, ERROR messages (recommended)

## Configuration options (`gracenote2epg.xml`)
- `<setting id="useragent">Mozilla/5.0...</setting>`: Custom User-Agent string for HTTP requests
- `<setting id="zipcode">92101</setting>`: US Zip or Canada postal code
- `<setting id="lineupcode">lineupId</setting>`: Lineup identifier from Gracenote
- `<setting id="lineup">Local Over the Air Broadcast</setting>`: Lineup description
- `<setting id="device">-</setting>`: Device identifier
- `<setting id="days">1</setting>`: Number of TV guide days (1-14)
- `<setting id="redays">1</setting>`: Number of days to retain cached data
- `<setting id="slist"></setting>`: Station list (comma-separated channel IDs)
- `<setting id="stitle">false</setting>`: Include series title in episode title
- `<setting id="xdetails">true</setting>`: Download extra Movie or Series details
- `<setting id="xdesc">true</setting>`: Append extra details to default TV show description
- `<setting id="epgenre">3</setting>`: Episode genre handling
- `<setting id="epicon">1</setting>`: Include episode icons/thumbnails
- `<setting id="usern"></setting>`: Username to access TVH server, anonymous if both `usern` + `passw` are empty
- `<setting id="passw"></setting>`: Password to access TVH server
- `<setting id="tvhurl">127.0.0.1</setting>`: IP address to TVH server
- `<setting id="tvhport">9981</setting>`: Port of TVH server
- `<setting id="tvhmatch">true</setting>`: Enable TVHeadend integration (channel fetching and matching)
- `<setting id="chmatch">true</setting>`: Enable channel name matching

## TVHeadend (TVH) Auto-Channel Fetching
This feature is controlled by the `tvhmatch` setting. When `tvhmatch=true`, the grabber will automatically connect to TVHeadend to fetch the channel list and filter downloaded data accordingly.

Configuration for TVHeadend integration:
* `<setting id="tvhmatch">true</setting>`: Enable TVHeadend integration (fetches channels and enables matching)
* `<setting id="usern"></setting>`: Username (leave empty for anonymous access)
* `<setting id="passw"></setting>`: Password (leave empty for anonymous access)
* `<setting id="tvhurl">127.0.0.1</setting>`: TVHeadend server IP
* `<setting id="tvhport">9981</setting>`: TVHeadend server port
* `<setting id="chmatch">true</setting>`: Enable channel name matching

For anonymous access, you must have a `*` user defined in TVH with minimally:
* Change parameters: `Rights`
* Allowed networks: `127.0.0.1` or `0.0.0.0;::/0`

TVHeadend integration can be disabled by setting `<setting id="tvhmatch">false</setting>`. It can also be set to use another user account by filling in the `usern` and `passw` fields.

## Installation: Synology DSM6/DSM7 TVH Server:
Available in the SynoCommunity tvheadend package for DSM6-7 since v4.3.20210612-29
* https://synocommunity.com/package/tvheadend

**DSM7** file structure:
```
/var/packages/tvheadend/target/bin
└── tv_grab_gracenote2epg
/var/packages/tvheadend/var/epggrab
├── cache
│   ├── *.json
│   └── xmltv.xml
├── conf
│   └── gracenote2epg.xml
└── log 
    └── gracenote2epg.log
```

**DSM6** file structure:
```
/var/packages/tvheadend/target/bin
└── tv_grab_gracenote2epg
/var/packages/tvheadend/target/var/epggrab
├── cache
│   ├── *.json
│   └── xmltv.xml
├── conf
│   └── gracenote2epg.xml
└── log 
    └── gracenote2epg.log
```

### Manual Installation
1. Install `tv_grab_gracenote2epg` script in `/usr/local/bin` or `/var/packages/tvheadend/target/bin`
2. Install `gracenote2epg.xml` configuration file under tvheadend `epggrab/conf` directory
3. Manually adjust `gracenote2epg.xml` configuration file as needed or use command-line options

### Testing
To test `tv_grab_gracenote2epg` EPG grabber under Synology DSM:
```bash
$ sudo su -s /bin/bash sc-tvheadend -c '~/bin/tv_grab_gracenote2epg --capabilities'
baseline

$ sudo su -s /bin/bash sc-tvheadend -c '~/bin/tv_grab_gracenote2epg --description'  
North America (tvlistings.gracenote.com using gracenote2epg)

$ sudo su -s /bin/bash sc-tvheadend -c '~/bin/tv_grab_gracenote2epg --version'
4.0

$ sudo su -s /bin/bash sc-tvheadend -c '~/bin/tv_grab_gracenote2epg --days 1 --postal J3B1M4 --quiet'

$ ls -la ~sc-tvheadend/var/epggrab/cache/xmltv.xml
-rw-rw-rw- 1 sc-tvheadend tvheadend 16320858 Jun 13 07:43 /var/packages/tvheadend/target/var/epggrab/cache/xmltv.xml
```

## Installation: Docker TVHeadend Setup:
Installation is somewhat different where it uses the `hts` user account to handle the directory structure such as:
```
/usr/bin
└── tv_grab_gracenote2epg
/home/hts/gracenote2epg  
├── cache
│   ├── *.json
│   └── xmltv.xml
├── conf
│   └── gracenote2epg.xml
└── log 
    └── gracenote2epg.log
```

### Manual Installation
Create the directory structure and adjust permissions:
```bash
# mkdir -p /home/hts/gracenote2epg/conf
# mkdir -p /home/hts/gracenote2epg/log  
# mkdir -p /home/hts/gracenote2epg/cache
# chown -R hts:hts /home/hts/gracenote2epg
# chmod -R 0755 /home/hts/gracenote2epg
```

Copy the configuration and adjust permissions:
```bash
# cp gracenote2epg.xml /home/hts/gracenote2epg/conf
# chown hts:hts /home/hts/gracenote2epg/conf/gracenote2epg.xml
# chmod 644 /home/hts/gracenote2epg/conf/gracenote2epg.xml
```

Copy the script to /usr/bin and adjust permissions:
```bash
# cp tv_grab_gracenote2epg /usr/local/bin
# chmod 755 /usr/local/bin/tv_grab_gracenote2epg
```

## Usage Examples

### Basic Usage:
```bash
# Default execution with INFO logging
tv_grab_gracenote2epg

# Grab 3 days of data starting tomorrow
tv_grab_gracenote2epg --days 3 --offset 1

# Use specific postal code and output to file
tv_grab_gracenote2epg --zip 12979 --output /tmp/guide.xml
```

### Advanced Usage:
```bash
# Debug mode with custom configuration
tv_grab_gracenote2epg --debug --config-file /path/to/custom.xml

# Silent mode for automated scripts  
tv_grab_gracenote2epg --silent --days 7

# Custom base directory
tv_grab_gracenote2epg --base-dir /var/lib/gracenote2epg --days 2
```

### TVHeadend Integration:
```bash
# Test grabber capabilities (required by TVHeadend)
tv_grab_gracenote2epg --capabilities

# Test with quiet output (TVHeadend mode)
tv_grab_gracenote2epg --quiet --days 2
```

## Version 4.0 Features

### Modular Architecture:
- **gracenote2epg_config**: Configuration management with XML parsing
- **gracenote2epg_tvheadend**: TVHeadend integration with auto-detection
- **gracenote2epg_downloader**: Gracenote API data downloading with caching
- **gracenote2epg_parser**: Data parsing with icon URL fixing
- **gracenote2epg_xmltv**: XMLTV generation with validation
- **gracenote2epg_utils**: Utility functions for data processing
- **gracenote2epg_args**: Command-line argument parsing

### Improved Features:
- **Native CLI Support**: Full command-line interface without bash dependency
- **Configurable Logging**: Four logging levels (debug, info, warning, silent)
- **Icon URL Fixing**: Automatic conversion of icon IDs to full URLs
- **User-Agent Configuration**: Honors User-Agent from configuration file
- **Enhanced Error Handling**: Better error messages and validation
- **TVHeadend Auto-Detection**: Automatic channel filtering based on TVHeadend setup
- **Simplified TVH Integration**: Single `tvhmatch` parameter controls all TVHeadend features

### Breaking Changes from v3.x:
- Requires Python 3.6+
- New command-line interface options
- Modular file structure
- Configuration file renamed to `gracenote2epg.xml`
- Log file renamed to `gracenote2epg.log`
- Base directory changed to `~/gracenote2epg`
- Simplified TVHeadend configuration (removed `tvhoff`, use only `tvhmatch`)
