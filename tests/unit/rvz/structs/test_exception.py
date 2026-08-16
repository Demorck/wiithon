import unittest
from io import BytesIO

from unit.rvz._common import FLAG, exception_bytes

from wiithon.rvz.structs.exception import WiaException


class TestWiaExceptions(unittest.TestCase):
    def test_exception_locates_a_hash_in_the_chunk(self):
        digest = bytes(range(20))

        first = WiaException.read(BytesIO(exception_bytes(0x0354, digest)))
        self.assertEqual(first.offset, 0x0354)
        self.assertEqual(first.hash, digest)
        self.assertEqual((first.block, first.offset_in_block), (0, 0x354))

        last = WiaException.read(BytesIO(exception_bytes(0xFFEC)))
        self.assertEqual((last.block, last.offset_in_block), (63, 0x3EC))

    def test_reader_stops_at_the_end_of_the_entry(self):
        stream = BytesIO(exception_bytes(0) + FLAG)
        WiaException.read(stream)
        self.assertEqual(stream.read(4), FLAG)


if __name__ == '__main__':
    unittest.main()