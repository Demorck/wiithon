import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import typer

from wiithon.cli._common import PartTypeChoice, require_file, select_partitions
from wiithon.disc.enums import WiiPartType


class FakeEntry:
    def __init__(self, part_type: int) -> None:
        self.part_type = part_type


class FakeReader:
    """Minimal stand-in for WiiIsoReader: select_partitions only reads .partitions."""
    def __init__(self, *types: int) -> None:
        self.partitions = [FakeEntry(t) for t in types]


class TestSelectPartitions(unittest.TestCase):

    def test_returns_all_when_no_filter(self):
        reader = FakeReader(WiiPartType.DATA, WiiPartType.UPDATE)
        self.assertEqual(len(select_partitions(reader, None)), 2)

    def test_matches_every_choice(self):
        reader = FakeReader(WiiPartType.DATA, WiiPartType.UPDATE, WiiPartType.CHANNEL)
        cases = [
            (PartTypeChoice.data,    WiiPartType.DATA),
            (PartTypeChoice.update,  WiiPartType.UPDATE),
            (PartTypeChoice.channel, WiiPartType.CHANNEL),
        ]
        for choice, expected in cases:
            with self.subTest(choice=choice.value):
                selected = select_partitions(reader, choice)
                self.assertEqual([p.part_type for p in selected], [expected])

    def test_aborts_when_type_absent(self):
        reader = FakeReader(WiiPartType.DATA)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(typer.Exit) as ctx:
                select_partitions(reader, PartTypeChoice.channel)
        self.assertEqual(ctx.exception.exit_code, 1)

    def test_unknown_type_is_never_matched(self):
        reader = FakeReader(0x0E)
        with self.assertRaises(typer.Exit):
            select_partitions(reader, PartTypeChoice.data)


class TestRequireFile(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_rejects_missing_path(self):
        with self.assertRaises(typer.Exit):
            require_file(self.root / "nope.iso")

    def test_rejects_directory(self):
        with self.assertRaises(typer.Exit):
            require_file(self.root)

    def test_accepts_regular_file(self):
        target = self.root / "ok.bin"
        target.write_bytes(b"\x00")
        require_file(target)


if __name__ == "__main__":
    unittest.main()