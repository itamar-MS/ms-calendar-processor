#!/usr/bin/env python3
"""
Simple runner script for the calendar extractor.
This allows running the application from the project root directory.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from core.main import main

if __name__ == "__main__":
    main() 