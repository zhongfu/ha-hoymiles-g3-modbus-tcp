"""Test bootstrap (pytest): make the mapper module and the library importable.

mapper.py is imported standalone (bypassing the HA-importer package __init__), so
the component package dir itself goes on sys.path. The library dir provides
`hoymiles_g3_modbus_tcp.registers`.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
COMPONENT_DIR = ROOT / "custom_components" / "hoymiles_g3_modbus_tcp"
LIB_DIR = ROOT.parent / "hoymiles-g3-modbus-tcp"

sys.path.insert(0, str(COMPONENT_DIR))
if LIB_DIR.is_dir():
    sys.path.insert(0, str(LIB_DIR))
