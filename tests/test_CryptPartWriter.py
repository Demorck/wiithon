import os
import unittest
from io import BytesIO

from crypto.CryptPartReader import CryptPartReader
from crypto.CryptPartWriter import CryptPartWriter
from helpers.Constants import GROUP_SIZE
from structs.WiiPartitionEntry import read_parts
from structs.WiiPartitionHeader import WiiPartitionHeader

TEST_ISO_PATH = os.path.join(os.path.dirname(__file__), ".", "assets", "smg.iso")

class TestCryptoRoundtrip(unittest.TestCase):
    """
    """

    @unittest.skipUnless(os.path.exists(TEST_ISO_PATH), "Test ISO not found")
    def test_writer_roundtrip(self) -> None:
        with open(TEST_ISO_PATH, "rb") as f:
            parts = read_parts(f)
            data_part = next(p for p in parts if p.part_type == 0)

            f.seek(data_part.offset)
            part_header = WiiPartitionHeader.read(f)
            title_key = part_header.ticket.title_key
            data_offset = data_part.offset + part_header.data_offset

            # First group
            f.seek(data_offset)
            raw_group_original = f.read(GROUP_SIZE)

        self.assertEqual(len(raw_group_original), GROUP_SIZE)

        iso_stream = BytesIO(raw_group_original)
        reader = CryptPartReader(iso_stream, data_offset=0, title_key=title_key)

        decrypted_data = reader.read_at(0, 0x1F0000)
        self.assertEqual(len(decrypted_data), 0x1F0000)

        out_stream = BytesIO()
        writer = CryptPartWriter(out_stream, data_offset=0, title_key=title_key)
        writer.write(decrypted_data)
        writer.close()

        out_stream.seek(0)
        raw_group_reconstructed = out_stream.read(GROUP_SIZE)

        self.assertEqual(len(raw_group_reconstructed), GROUP_SIZE)

        # The roundtrip and the original needs to be the exact same since its hashes
        self.assertEqual(raw_group_reconstructed, raw_group_original)


if __name__ == "__main__":
    unittest.main()
