import os
import unittest

from WiiIsoReader import WiiIsoReader
from structs.DiscHeader import DiscHeader
from file_system_table.FSTNode import FSTDirectory

TEST_ISO_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "smg.iso")


@unittest.skipUnless(os.path.exists(TEST_ISO_PATH), "Test ISO not found")
class TestWiiIsoReader(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        """Open the ISO once for all tests"""
        cls.reader = WiiIsoReader(TEST_ISO_PATH)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the ISO after all tests"""
        cls.reader.close()

    def test_disc_header(self) -> None:
        """Test that the disc header is correctly read"""
        header = self.reader.disc_header
        self.assertIsInstance(header, DiscHeader)
        self.assertEqual(len(header.game_id), 6)
        self.assertEqual(header.wii_magic_word, 0x5D1C9EA3)

    def test_partitions_found(self) -> None:
        """Test that at least one partition is found"""
        self.assertGreater(len(self.reader.partitions), 0)

    def test_data_partition_exists(self) -> None:
        """Test that a DATA partition (type 0) exists"""
        data = self.reader.get_data_partition()
        self.assertIsNotNone(data)
        self.assertEqual(data.part_type, 0)

    def test_game_id(self) -> None:
        """Test that the game ID matches Super Mario Galaxy NTSC - U"""
        self.assertEqual(self.reader.disc_header.game_id, b'RMGE01')

    def test_game_title(self) -> None:
        """Test that the game title is readable"""
        title = self.reader.disc_header.game_title
        self.assertIsInstance(title, str)
        self.assertGreater(len(title.strip()), 0)
        self.assertEqual(title.strip(), "SUPER MARIO GALAXY")


@unittest.skipUnless(os.path.exists(TEST_ISO_PATH), "Test ISO not found")
class TestWiiPartitionReadInfo(unittest.TestCase):
    """Integration tests for opening and reading a partition"""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the ISO and the DATA partition"""
        cls.reader = WiiIsoReader(TEST_ISO_PATH)
        data_entry = cls.reader.get_data_partition()
        cls.partition = cls.reader.open_partition(data_entry)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.reader.close()

    def test_internal_header(self) -> None:
        """Test that the internal (decrypted) disc header is valid"""
        header = self.partition.internal_header
        self.assertEqual(header.wii_magic_word, 0x5D1C9EA3)
        self.assertIn("MARIO", header.game_title.upper())

    def test_fst_not_empty(self) -> None:
        """Test that the FST contains entries"""
        self.assertGreater(len(self.partition.fst.entries), 0)

    def test_fst_root_is_directory(self) -> None:
        """Test that top-level FST entries contain directories"""
        has_dir = any(isinstance(e, FSTDirectory)
                      for e in self.partition.fst.entries)
        self.assertTrue(has_dir)

    def test_list_files(self) -> None:
        """Test that list_files returns file paths"""
        files = self.partition.list_files()
        self.assertGreater(len(files), 0)
        # All paths should be strings
        for path in files:
            self.assertIsInstance(path, str)

    def test_read_nonexistent_file(self) -> None:
        """Test that reading a nonexistent file raises FileNotFoundError"""
        with self.assertRaises(FileNotFoundError):
            self.partition.read_file("feur/apagnan.txt")

    def test_read_dol(self) -> None:
        """Test reading the main DOL executable"""
        dol = self.partition.read_dol()
        self.assertGreater(len(dol), 0x100)

    def test_tmd_valid(self) -> None:
        """Test that the TMD was read correctly"""
        tmd = self.partition.tmd
        self.assertGreater(len(tmd.contents), 0)

    def test_certificates(self) -> None:
        """Test that 3 certificates were read"""
        self.assertEqual(len(self.partition.certificates), 3)


if __name__ == "__main__":
    unittest.main()