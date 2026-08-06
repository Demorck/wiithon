import unittest

from tests.cli._iso_case import IsoCliTestCase


class TestIsoInfo(IsoCliTestCase):

    def test_shows_game_id(self):
        result = self.invoke("iso", "info", self.iso)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("FEUR69", result.stdout)


class TestIsoList(IsoCliTestCase):

    def test_lists_data_partition(self):
        result = self.invoke("iso", "list", self.iso, "-p", "data")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("saint_bernard.jpg", result.stdout)

    def test_tree_mode(self):
        result = self.invoke("iso", "list", self.iso, "-t")
        self.assertEqual(result.exit_code, 0)

    def test_absent_partition_exits_with_1(self):
        result = self.invoke("iso", "list", self.iso, "-p", "channel")
        self.assertEqual(result.exit_code, 1)


class TestIsoExtract(IsoCliTestCase):

    def test_writes_files_to_disk(self):
        dest = self.temp_dir()
        result = self.invoke("iso", "extract", self.iso, str(dest))
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((dest / "data" / "saint_bernard.jpg").is_file())

class TestIsoCat(IsoCliTestCase):

    def test_prints_hexdump_offsets(self):
        result = self.invoke("iso", "cat", self.iso, "saint_bernard.jpg", "-n", "64")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("00000000", result.stdout)

    def test_unknown_path_exits_with_1(self):
        result = self.invoke("iso", "cat", self.iso, "nope.bin")
        self.assertEqual(result.exit_code, 1)

    def test_leading_slash_is_tolerated(self):
        result = self.invoke("iso", "cat", self.iso, "/saint_bernard.jpg", "-n", "16")
        self.assertEqual(result.exit_code, 0)


class TestIsoExtractFile(IsoCliTestCase):

    def test_extracts_a_single_file(self):
        dest = self.temp_dir()
        result = self.invoke("iso", "extract", self.iso, str(dest), "--file", "saint_bernard.jpg")
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((dest / "saint_bernard.jpg").is_file())
        self.assertFalse((dest / "data").exists())

    def test_unknown_path_exits_with_1(self):
        dest = self.temp_dir()
        result = self.invoke("iso", "extract", self.iso, str(dest), "--file", "nope.bin")
        self.assertEqual(result.exit_code, 1)

if __name__ == "__main__":
    unittest.main()