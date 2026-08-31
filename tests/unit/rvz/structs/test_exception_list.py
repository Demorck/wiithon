import struct
import unittest
from io import BytesIO

from tests.unit.rvz._common import FLAG, exception_bytes

from wiithon.rvz.structs.exception_list import WiaExceptionList


class TestWiaExceptionList(unittest.TestCase):
    def test_list_keeps_the_entries_in_order(self):
        raw = struct.pack(">H", 2) + exception_bytes(0x10, b"A" * 20) + exception_bytes(0x20, b"B" * 20)
        listing = WiaExceptionList.read(BytesIO(raw))

        self.assertEqual(len(listing), 2)
        self.assertEqual([entry.offset for entry in listing.exceptions], [0x10, 0x20])
        self.assertEqual(listing.exceptions[1].hash, b"B" * 20)

    def test_a_clean_group_reads_as_an_empty_list(self):
        stream = BytesIO(struct.pack(">H", 0) + FLAG)
        self.assertEqual(len(WiaExceptionList.read(stream)), 0)
        self.assertEqual(stream.read(4), FLAG)


if __name__ == '__main__':
    unittest.main()