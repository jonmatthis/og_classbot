""" An ai-enabled chatbot """
__version__ = "v0.1.0"

import sys
from pathlib import Path

base_package_path = Path(__file__).parent.parent
sys.path.insert(0, str(base_package_path))  # add parent directory to sys.path
