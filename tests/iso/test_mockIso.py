
import pytest
from iso._common import GAME_ID, ISO_PATH

from wiithon.disc.layout import WII_MAGIC_WORD


@pytest.fixture(scope="module")
def header():
    if not ISO_PATH.exists():
        pytest.skip("ISO not found")
    with ISO_PATH.open("rb") as f:
        return f.read(0x20)


def test_game_id(header):
    assert header[0:6] == GAME_ID


def test_wii_magic(header):
    assert int.from_bytes(header[0x18:0x1C], "big") == WII_MAGIC_WORD