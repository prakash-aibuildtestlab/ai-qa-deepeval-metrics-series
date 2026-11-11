import sys
from pathlib import Path


SUITE_ROOT = Path(__file__).resolve().parents[1]

if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))