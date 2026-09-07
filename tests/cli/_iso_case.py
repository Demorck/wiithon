import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from wiithon.cli import app

ISO_PATH = Path(__file__).parent.parent / "mock_iso" / "test.iso"

WIDE_ENV = {"COLUMNS": "200"}


class IsoCliTestCase(unittest.TestCase):
    """Base class for CLI tests that need the mock ISO built by the `iso` CI job."""

    @classmethod
    def setUpClass(cls):
        if not ISO_PATH.exists():
            raise unittest.SkipTest("mock ISO not built - see the `iso` job in tests.yml")
        cls.iso = str(ISO_PATH)

    def setUp(self):
        self.runner = CliRunner()

    def invoke(self, *args: str):
        return self.runner.invoke(app, list(args), env=WIDE_ENV)

    def temp_dir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)