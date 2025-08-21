#!/usr/bin/env python3
"""
gracenote2epg.__main__ - Module entry point
"""

import sys


def main():
    """Main entry point for console scripts"""
    try:
        from .main import main as script_main

        return script_main()
    except ImportError as e:
        print(f"Error: Could not import main script: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
