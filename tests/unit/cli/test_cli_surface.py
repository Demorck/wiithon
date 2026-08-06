import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from wiithon.cli import app

COMMANDS = [
    ["iso", "info"], ["iso", "list"], ["iso", "extract"],
    ["dol", "caves"],
    ["rarc", "info"], ["rarc", "extract"], ["rarc", "pack"],
]


class TestCliSurface(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_root_help_lists_every_group(self):
        result = self.runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        for group in ("iso", "dol", "rarc"):
            with self.subTest(group=group):
                self.assertIn(group, result.stdout)

    def test_every_command_is_registered(self):
        for command in COMMANDS:
            with self.subTest(command=" ".join(command)):
                result = self.runner.invoke(app, [*command, "--help"])
                self.assertEqual(result.exit_code, 0)


class TestFileValidation(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_missing_file_exits_with_1(self):
        for command in (["iso", "info"], ["iso", "list"], ["rarc", "info"], ["dol", "caves"]):
            with self.subTest(command=" ".join(command)):
                result = self.runner.invoke(app, [*command, str(self.root / "nope")])
                self.assertEqual(result.exit_code, 1)


if __name__ == "__main__":
    unittest.main()