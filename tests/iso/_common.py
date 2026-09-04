import os
import unittest
from pathlib import Path
from typing import BinaryIO

from wiithon.crypto.layout import BLOCK_HEADER_SIZE, BLOCK_PER_GROUP, BLOCK_SIZE
from wiithon.rvz.reader import WiaReader

# Paths
MOCK_DIR = Path(__file__).parent.parent / "mock_iso"
WIA_PATH = MOCK_DIR / "test.wia"
RVZ_PATH = MOCK_DIR / "test.rvz"
ISO_PATH = MOCK_DIR / "test.iso"

# Suffixes the shared checks are run against
IMAGE_SUFFIXES = {".wia", ".rvz"}

# Decorators
needs_iso = unittest.skipUnless(ISO_PATH.is_file(), "ISO not found")
needs_wia = unittest.skipUnless(WIA_PATH.is_file(), "WIA not found")
needs_rvz = unittest.skipUnless(RVZ_PATH.is_file(), "RVZ not found")
needs_both = unittest.skipUnless(WIA_PATH.is_file() and RVZ_PATH.is_file(), "WIA or RVZ not found")
needs_slow = unittest.skipUnless(
    os.environ.get("WIITHON_SLOW"), "set WIITHON_SLOW to walk whole images"
)

# WIA/RVZ Tests
EXCEPTION_SIZE = 22
COMPARE_BUFFER = 8 << 20

# Game information
GAME_ID = b"FEUR69"
ISO_SIZE = 4_699_979_776


def discover_images() -> list[Path]:
    """
    Every WIA or RVZ sitting next to the mock ISO

    Returns:
        The images the shared checks run against, in a stable order
    """
    if not MOCK_DIR.is_dir():
        return []

    return sorted(path for path in MOCK_DIR.iterdir() if path.suffix in IMAGE_SUFFIXES)


def patched_hash_offsets(reader: WiaReader) -> set[int]:
    """
    Every hash the writer had to fix up, addressed from the start of the partition

    An exception offset is relative to the chunk that carries it and chunks are cut
    differently by every writer. Absolute offsets are the only common ground

    Args:
        reader: An open image

    Returns:
        One offset per patched hash
    """
    blocks_per_chunk = reader.disc.chunk_size // BLOCK_SIZE
    blocks_per_list = min(blocks_per_chunk, BLOCK_PER_GROUP)
    offsets = set()

    for partition in reader.partitions:
        for segment in partition.segments:
            for chunk in range(segment.group_count):
                lists = reader.read_exception_lists(segment.group_index + chunk)

                for sub_group, listing in enumerate(lists):
                    first_block = chunk * blocks_per_chunk + sub_group * blocks_per_list
                    for exception in listing.exceptions:
                        block = first_block + exception.block
                        offsets.add(block * BLOCK_HEADER_SIZE + exception.offset_in_block)

    return offsets


def compare_range(rebuilt: BinaryIO, reference: BinaryIO, offset: int, size: int) -> None:
    """
    Compare one slice of a rebuilt image with the same slice of the reference ISO

    Args:
        rebuilt: The image that was just rebuilt
        reference: The ISO it should be identical to
        offset: Where the slice starts
        size: How many bytes to compare

    Raises:
        AssertionError: At the first byte that differs or if a read comes up short
    """
    rebuilt.seek(offset)
    reference.seek(offset)
    position = offset

    while size:
        count = min(COMPARE_BUFFER, size)
        left, right = rebuilt.read(count), reference.read(count)

        if left != right:
            for i, (from_rebuilt, from_reference) in enumerate(zip(left, right, strict=False)):
                if from_rebuilt != from_reference:
                    raise AssertionError(
                        f"rebuilt image differs at {position + i:#x}: "
                        f"{from_rebuilt:#04x} instead of {from_reference:#04x}"
                    )
            raise AssertionError(f"short read at {position:#x}")

        position += count
        size -= count