# Changelog

All notable changes to gracenote2epg will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5] - Planned
### TODO
- **IMDB**: Add IMDB support
- **Rotten Tomatoes**: Add Rotten Tomatoes support
- **Country**: Use actual country of origin, if unavailable discard

## [1.4] - Current Release
### Added
- **Simplified Lineup Configuration**: Single `lineupid` setting replaces complex multi-parameter setup
  - Auto-detection with `lineupid=auto` for Over-the-Air (OTA) channels
  - Direct copy from tvtv.com URLs (auto-normalized to API format)
  - Complete provider format support for Cable/Satellite (e.g., `CAN-0005993-X`)
  - Automatic device type detection (`-` for OTA, `X` for Cable/Satellite)
  - Backward compatibility with legacy configuration (automatic migration)
- **Lineup Testing Tool**: New `--show-lineup` command-line option for configuration validation
  - Test postal/ZIP codes before configuration: `--show-lineup --zip 92101`
  - Simplified output mode for quick verification
  - Debug mode with detailed technical information: `--show-lineup --zip 92101 --debug`
  - Manual validation URLs and step-by-step instructions
  - Complete API URL generation for manual testing
- **Enhanced Command-Line Interface**: New `--lineupid` option for direct lineup specification
  - Override configuration lineup from command line: `--lineupid CAN-OTAJ3B1M4`
  - Consistent with other command-line options (`--zip`, `--postal`, `--langdetect`)
  - Supports all lineup formats (auto, tvtv.com format, complete provider format)
  - **Smart Location Intelligence**: Automatic postal/ZIP extraction from OTA lineups
    - `--lineupid CAN-OTAJ3B1M4` automatically provides postal code `J3B1M4`
    - `--lineupid USA-OTA90210` automatically provides ZIP code `90210`
    - Consistency validation when both lineup and location are explicitly provided
    - Eliminates need to specify both parameters for OTA configurations
- **Intelligent Log Rotation**: Multi-period rotation with content analysis for daily/weekly/monthly modes
  - Analyzes actual log content instead of file timestamps for accurate rotation decisions
  - Separates complete periods into individual backup files (e.g., W31, W32, W33)
  - Visible rotation messages in logs with clear reporting
  - Compatible with `tail -f` and log monitoring tools using copytruncate strategy
- **Python wheel compatible**: Now allows generating a python wheel redistributable package
- **Comprehensive packaging**: Both wheel (.whl) and source (.tar.gz) distributions
- **Multiple command interfaces**: gracenote2epg, tv_grab_gracenote2epg, and module execution

### Changed
- **Configuration Format**: Updated to version 5 with simplified lineup settings
  - Single `lineupid` parameter replaces `auto_lineup`, `lineupcode`, `lineup`, and `device`
  - Automatic migration from legacy configuration formats with backup creation
  - Cleaner configuration file structure with better organization
- **Logging Optimization**: Reduced duplication in lineup configuration logging
  - Single detailed report in configuration summary instead of multiple repetitive messages
  - Debug-level logging for internal lineup operations to reduce log noise
  - Simplified final summary with essential information only
- **Enhanced documentation**: Separated user and developer documentation with comprehensive guides
  - New LINEUPID.md for detailed lineup configuration instructions
  - Updated README.md with lineup testing examples and validation procedures
  - Improved troubleshooting section with specific lineup-related solutions

### Fixed
- **Configuration Migration**: Robust handling of legacy configuration formats
  - Automatic detection and migration of deprecated settings
  - Preserves user customizations while updating to new format
  - Clear migration logging with backup file creation
- **Lineup Detection**: Improved reliability of automatic lineup detection
  - Better error handling for invalid postal/ZIP codes
  - Enhanced validation of lineup formats from tvtv.com
  - Fallback mechanisms for edge cases and malformed inputs

## [1.3] - Previous Release
### Added
- **Categories Translation**: Automatic English/French/Spanish category translation using .po files
  - Proper capitalization rules per language (Title Case for English, Sentence case for French/Spanish)
  - Smart fallback when translation files unavailable
  - Requires `polib` for full functionality (`pip install polib`)
- **Rating system**: Enhanced with MPAA system support

### Changed
- **Credits**: Use proper `<image>` sub-element instead of src attribute - now strict XMLTV DTD compliant
- **`episode-num xmltv_ns`**: Use spaces around dots per DTD standard

### Fixed
- **Stereo detection**: Fixed to properly detect STEREO tag
- **Language Cache**: Allow handling of malformed XML when scrubbing previous xmltv

## [1.2] - Older Release
### Added
- **Language Cache**: 95-100% cache efficiency with automatic reuse of previous language detections
- **Enhanced XMLTV Metadata**: New DTD-compliant fields (language, country, video, audio) controlled by xdetails configuration
- **Modular Language Detection**: New gracenote2epg_language module with LanguageDetector class for better architecture
- **Smart Metadata Logic**: Country detection from zipcode format, stereo audio from tags, aspect ratio from content age

### Changed
- **Performance Optimization**: Eliminates redundant `langdetect` calls, reducing XMLTV generation time from ~15 minutes to ~2-3 minutes

## [1.1] - Older Release
### Added
- **Progress Tracking**: Real-time progress indicators for long operations
- **Migration Documentation**: Complete migration guide from other EPG grabbers
- **Extended Details Improvements**: Better handling and corrections for xdetails and xdesc configuration
- **Strict XMLTV DTD Compliance**: Full DTD compliance except for actor photo `src=` attribute extension
- **XMLTV Generation Progress**: Percentage progress indicators during XML generation (especially useful for langdetect operations)
- **Download Progress Counters**: Added "x/y" counters for extended details downloads to show remaining downloads
- **Cache Refresh Options**: New `--refresh X` and `--norefresh` command-line options for flexible cache management
- **Configuration Version 4**: Updated configuration schema to support new refresh options

### Fixed
- **Directory Permissions Fix**: Create directories with proper 755 permissions instead of 777
- **Enhanced Synology Detection**: Improved system detection for DSM6/DSM7 path selection

## [1.0] - Initial Release
### Added
- **Python Modularization**: Based on edit4ever's script.module.zap2epg with tv_grab_zap2epg improvements and Python modular architecture
- **Multi-Language Support**: Automatic French/English/Spanish detection with localized translations
- **Reliable Language Detection**: langdetect library integration with configurable enable/disable options
- **Enhanced XMLTV Generation**: Line breaks for better Kodi display, proper language attributes
- **Intelligent Cache Management**: Smart caching with 95%+ efficiency  
- **Flexible Logging System**: File-based logging with optional console output and language statistics
- **Improved Error Handling**: Robust downloading and parsing with WAF protection
- **Better Debugging**: Detailed statistics including language distribution and configurable verbosity
- **Platform Auto-detection**: Smart directory configuration for Raspberry Pi, Synology, etc.
- **Full Backward Compatibility**: Works with existing zap2epg configurations and cache
- **Kodi/TVheadend Integration**: Maintains original design goals for media center use with enhanced formatting
