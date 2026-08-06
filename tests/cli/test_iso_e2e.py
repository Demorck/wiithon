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


if __name__ == "__main__":
    unittest.main()