#!/usr/bin/env python3
"""
gracenote2epg.__main__ - Module entry point

Allows running gracenote2epg as a module:
    python -m gracenote2epg --help
    python -m gracenote2epg --days 7 --zip 92101
"""

import sys
from pathlib import Path

# Import and run the main function
if __name__ == '__main__':
    # Import the main script function
    try:
        # Try importing from the parent directory
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        
        # Import the main function from gracenote2epg.py
        import gracenote2epg
        sys.exit(gracenote2epg.main())
        
    except ImportError as e:
        print(f"Error importing gracenote2epg: {e}", file=sys.stderr)
        print("Please ensure gracenote2epg.py is in the parent directory", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running gracenote2epg: {e}", file=sys.stderr)
        sys.exit(1)
