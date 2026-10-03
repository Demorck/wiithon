import unittest

from tests.iso._common import ISO_PATH, WIA_PATH, needs_iso, needs_wia

from wiithon.crypto.blocks import decrypt_block_header, hash_group
from wiithon.crypto.layout import (
    BLOCK_DATA_SIZE,
    BLOCK_HEADER_SIZE,
    BLOCK_PER_GROUP,
    BLOCK_SIZE,
    GROUP_SIZE,
)
from wiithon.rvz.patching import hash_exceptions
from wiithon.rvz.reader import WiaReader


@needs_wia
@needs_iso
class TestHashExceptionsAgainstADisc(unittest.TestCase):
    """
    What a reader gets wrong must be exactly what the writer listed

    Checked on an image whose chunk is one hash group, so a chunk can be hashed on
    its own. Smaller chunks only change how the same exceptions are cut up, which
    the round trip covers instead.
    """

    def test_found_exceptions_match_the_announced_ones(self):
        reader = WiaReader(str(WIA_PATH))
        self.addCleanup(reader.close)
        self.assertEqual(reader.disc.chunk_size, GROUP_SIZE)

        iso = ISO_PATH.open("rb")
        self.addCleanup(iso.close)

        for partition in reader.partitions:
            first = partition.segments[0].first_block

            for segment in partition.segments:
                for i in range(segment.group_count):
                    index = segment.group_index + i
                    block = segment.first_block - first + i * BLOCK_PER_GROUP
                    lists, payload = reader.read_partition_group(
                        index, block * BLOCK_DATA_SIZE
                    )

                    buffer = bytearray(GROUP_SIZE)
                    for b in range(BLOCK_PER_GROUP):
                        piece = payload[b * BLOCK_DATA_SIZE:(b + 1) * BLOCK_DATA_SIZE]
                        at = b * BLOCK_SIZE + BLOCK_HEADER_SIZE
                        buffer[at:at + len(piece)] = piece
                    hash_group(buffer)

                    blocks = min(BLOCK_PER_GROUP, segment.block_count - i * BLOCK_PER_GROUP)
                    found = 0
                    for b in range(blocks):
                        iso.seek(segment.offset + (i * BLOCK_PER_GROUP + b) * BLOCK_SIZE)
                        stored = decrypt_block_header(
                            iso.read(BLOCK_HEADER_SIZE), partition.title_key
                        )
                        recomputed = bytes(buffer[b * BLOCK_SIZE:][:BLOCK_HEADER_SIZE])
                        found += len(hash_exceptions(stored, recomputed))

                    with self.subTest(group=index):
                        self.assertEqual(found, sum(len(one) for one in lists))