from pathlib import Path
import sys

# Ensure repository root is on sys.path when running this file directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastsearch.gui.app import run_gui

if __name__ == "__main__":
    run_gui()
