import unittest
from pathlib import Path

# Paths
MOCK_DIR = Path(__file__).parent.parent / "mock_iso"
WIA_PATH = MOCK_DIR / "test.wia"
RVZ_PATH = MOCK_DIR / "test.rvz"
ISO_PATH = MOCK_DIR / "test.iso"

# Decorator
needs_iso = unittest.skipUnless(ISO_PATH.is_file(), "ISO not found")
needs_wia = unittest.skipUnless(WIA_PATH.is_file(), "WIA not found")
needs_rvz = unittest.skipUnless(RVZ_PATH.is_file(), "RVZ not found")
needs_both = unittest.skipUnless(WIA_PATH.is_file() and RVZ_PATH.is_file(), "WIA or RVZ not found")

# WIA/RVZ Tests
EXCEPTION_SIZE = 22
COMPARE_BUFFER = 8 << 20

# Game information
GAME_ID = b"FEUR69"
ISO_SIZE = 4_699_979_776