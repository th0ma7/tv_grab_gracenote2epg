#!/usr/bin/env python3
"""
Setup script for gracenote2epg package
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read version from package
def get_version():
    """Extract version from gracenote2epg/__init__.py - fail if not found"""
    init_file = this_directory / "gracenote2epg" / "__init__.py"

    if not init_file.exists():
        raise FileNotFoundError(f"Cannot find {init_file}")

    content = init_file.read_text()
    for line in content.splitlines():
        if line.startswith('__version__'):
            # Extract version from line like: __version__ = "1.4"
            if '"' in line:
                return line.split('"')[1]
            elif "'" in line:
                return line.split("'")[1]

    # No fallback - strict failure
    raise ValueError(
        f"No __version__ found in {init_file}. "
    )

setup(
    name="gracenote2epg",
    version=get_version(),
    description="North America TV Guide Grabber for gracenote.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="th0ma7",
    author_email="th0ma7@users.noreply.github.com",
    url="https://github.com/th0ma7/gracenote2epg",
    license="GPL-3.0-only",  # SPDX license identifier
    license_files=['LICENSE'],

    # Package configuration
    packages=find_packages(),
    python_requires=">=3.7",

    # Dependencies
    install_requires=[
        "requests>=2.25.0",
    ],
    extras_require={
        "full": [
            "langdetect>=1.0.9",  # For language detection
            "polib>=1.1.0",       # For translations
        ],
        "translations": ["polib>=1.1.0"],
        "langdetect": ["langdetect>=1.0.9"],
    },

    # Include package data (locales, config template, main script)
    package_data={
        'gracenote2epg': [
            'locales/*/LC_MESSAGES/*.po',
            'locales/*/LC_MESSAGES/*.mo',
            'locales/*.pot',
            'gracenote2epg_main.py',  # Include the main script
        ]
    },
    include_package_data=True,

    # Console entry points - both names for compatibility
    entry_points={
        'console_scripts': [
            'gracenote2epg=gracenote2epg.__main__:main',
            'tv_grab_gracenote2epg=gracenote2epg.__main__:main',
        ],
    },

    # Additional files - documentation, config, and wrapper scripts
    data_files=[
        ('share/doc/gracenote2epg', [
            'README.md',
            'LICENSE',
            'PACKAGING.md',
            'CHANGELOG.md',
            'LOG_ROTATION.md',
            'LINEUPID.md',
            'CACHE_RETENTION_POLICIES.md'
        ]),
        ('share/gracenote2epg', ['gracenote2epg.xml']),
        ('bin', ['tv_grab_gracenote2epg']),  # Only the XMLTV standard wrapper
    ],

    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Communications",
    ],

    # Keywords for discovery
    keywords="tv guide epg xmltv gracenote tvheadend kodi",

    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/th0ma7/gracenote2epg/issues",
        "Source": "https://github.com/th0ma7/gracenote2epg",
        "Documentation": "https://github.com/th0ma7/gracenote2epg#readme",
    },
)
