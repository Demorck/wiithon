import struct
import unittest
from io import BytesIO
from unittest.mock import MagicMock

from builder.CopyBuilder import CopyBuilder
from builder.WiiDiscBuilder import WiiDiscBuilder, _align_up, _pad_to
from crypto.CryptPartWriter import CryptPartWriter
from file_system_table.FSTNode import FSTDirectory, FSTFile
from structs.DiscHeader import DiscHeader
from structs.WiiPartitionEntry import WiiPartitionEntry

def _fake_fst_entries():
    """
    Tree:
        a.bin      (offset=0x1000, length=0x200)
        subdir/
            c.bin  (offset=0x2000, length=0x50)
    """
    a = FSTFile("a.bin", offset=0x1000, length=0x200)
    c = FSTFile("c.bin", offset=0x2000, length=0x50)
    d = FSTDirectory("subdir")
    d.children = [c]
    return [a, d]


def _make_copy_builder(entries=None):
    """Build a CopyBuilder with a mock WiiPartitionInfo"""
    if entries is None:
        entries = _fake_fst_entries()

    info = MagicMock()
    info.fst.entries = entries
    info.read_bi2.return_value      = b'\xBB' * 0x2000
    info.read_apploader.return_value = b'\xAA' * 0x20
    info.read_dol.return_value       = b'\xDD' * 0x40

    entry = WiiPartitionEntry()
    entry.part_type = 0

    return CopyBuilder(entry, info)

class TestAlignUp(unittest.TestCase):

    def test_already_aligned(self):
        self.assertEqual(_align_up(0x200000, 0x200000), 0x200000)

    def test_needs_alignment(self):
        self.assertEqual(_align_up(0x200001, 0x200000), 0x400000)

    def test_zero(self):
        self.assertEqual(_align_up(0, 0x8000), 0)

class TestPadTo(unittest.TestCase):

    def _make_writer(self):
        """Return a CryptPartWriter backed by BytesIO with a null key"""
        buf = BytesIO()
        return CryptPartWriter(buf, 0, b'\x00' * 16)

    def test_no_padding_needed(self):
        w = self._make_writer()
        w.write(b'\xAA' * 100)
        pos_before = w.current_position
        _pad_to(w, 100)
        self.assertEqual(w.current_position, pos_before)  # unchanged

    def test_pads_correct_amount(self):
        w = self._make_writer()
        w.write(b'\xAA' * 10)
        _pad_to(w, 50)
        self.assertEqual(w.current_position, 50)

    def test_raises_if_past_target(self):
        w = self._make_writer()
        w.write(b'\xAA' * 100)
        with self.assertRaises(ValueError):
            _pad_to(w, 50)

class TestCopyBuilderSourceFiles(unittest.TestCase):

    def test_source_offsets_captured(self):
        """Original offsets are saved at construction, before any mutation"""
        cb = _make_copy_builder()
        self.assertEqual(cb._source_files, [(0x1000, 0x200), (0x2000, 0x50)])

    def test_source_files_unchanged_after_assign(self):
        """assign_file_offsets must not alter _source_files"""
        cb = _make_copy_builder()
        cb.assign_file_offsets(0x8000)
        self.assertEqual(cb._source_files, [(0x1000, 0x200), (0x2000, 0x50)])


class TestCopyBuilderAssignOffsets(unittest.TestCase):

    def test_sequential_assignment(self):
        cb = _make_copy_builder()
        cb.assign_file_offsets(0x8000)

        entries = cb._fst_to_bytes.entries
        # a.bin → 0x8000
        self.assertEqual(entries[0].offset, 0x8000)
        # c.bin → 0x8000 + 0x200
        self.assertEqual(entries[1].children[0].offset, 0x8000 + 0x200)

    def test_lengths_unchanged(self):
        cb = _make_copy_builder()
        cb.assign_file_offsets(0x8000)

        entries = cb._fst_to_bytes.entries
        self.assertEqual(entries[0].length, 0x200)
        self.assertEqual(entries[1].children[0].length, 0x50)

    def test_empty_fst(self):
        cb = _make_copy_builder(entries=[])
        cb.assign_file_offsets(0x8000)

class TestCopyBuilderWriteFileData(unittest.TestCase):

    def test_reads_from_source_offsets(self):
        """write_file_data reads using the ORIGINAL source offsets, not mutated ones"""
        cb = _make_copy_builder()
        cb.assign_file_offsets(0x8000)

        calls = []
        cb._info.crypto.read_at.side_effect = lambda off, ln: calls.append((off, ln)) or b'\x00' * ln

        writer = MagicMock()
        writer.current_position = 0
        cb.write_file_data(writer)

        self.assertIn((0x1000, 0x200), calls)
        self.assertIn((0x2000, 0x50),  calls)

    def test_zero_length_files_skipped(self):
        """Files with length=0 are not read from source"""
        entries = [FSTFile("empty.bin", offset=0xAAAA, length=0)]
        cb = _make_copy_builder(entries=entries)
        writer = MagicMock()
        cb.write_file_data(writer)

    def test_returns_file_count(self):
        cb = _make_copy_builder()        # 2 files: a.bin + c.bin
        cb._info.crypto.read_at.return_value = b'\x00'
        writer = MagicMock()
        count = cb.write_file_data(writer)
        self.assertEqual(count, 2)

    def test_progress_callback(self):
        cb = _make_copy_builder()
        cb._info.crypto.read_at.return_value = b'\x00' * 0x10
        writer = MagicMock()

        progress_values = []
        cb.write_file_data(writer, progress_cb=progress_values.append)

        self.assertEqual(len(progress_values), 2)
        self.assertLessEqual(progress_values[-1], 100)
        self.assertGreater(progress_values[-1], 0)

class TestWiiDiscBuilderFinish(unittest.TestCase):

    _BUF_SIZE = 0x50000

    def _run_finish(self, builder):
        out = BytesIO(b'\x00' * self._BUF_SIZE)
        builder.finish(out)
        return out

    def test_disc_header_at_offset_0(self):
        dh = DiscHeader()
        dh.game_id = b'RMGE01'
        dh.wii_magic_word = 0x5D1C9EA3

        out = self._run_finish(WiiDiscBuilder(dh, b'\x00' * 0x20))
        out.seek(0)
        self.assertEqual(out.read(6), b'RMGE01')

    def test_region_at_0x4E000(self):
        region = bytes(range(0x20))
        out = self._run_finish(WiiDiscBuilder(DiscHeader(), region))
        out.seek(0x4E000)
        self.assertEqual(out.read(0x20), region)

    def test_partition_table_no_partitions(self):
        out = self._run_finish(WiiDiscBuilder(DiscHeader(), b'\x00' * 0x20))
        out.seek(0x40000)
        count = struct.unpack('>I', out.read(4))[0]
        self.assertEqual(count, 0)

    def test_partition_table_one_entry(self):
        builder = WiiDiscBuilder(DiscHeader(), b'\x00' * 0x20)

        e = WiiPartitionEntry()
        e.offset    = 0xF800000
        e.part_type = 0
        builder._partitions.append((e, 0x100000))

        out = self._run_finish(builder)

        out.seek(0x40000)
        count           = struct.unpack('>I', out.read(4))[0]
        entries_shifted = struct.unpack('>I', out.read(4))[0]
        self.assertEqual(count,           1)
        self.assertEqual(entries_shifted, 0x40020 >> 2)

        out.seek(0x40020)
        off_shifted = struct.unpack('>I', out.read(4))[0]
        part_type   = struct.unpack('>I', out.read(4))[0]
        self.assertEqual(off_shifted, 0xF800000 >> 2)
        self.assertEqual(part_type,   0)

    def test_groups_1_3_are_empty(self):
        builder = WiiDiscBuilder(DiscHeader(), b'\x00' * 0x20)
        out = self._run_finish(builder)

        out.seek(0x40008)
        for group_index in range(1, 4):
            count = struct.unpack('>I', out.read(4))[0]
            out.read(4)
            self.assertEqual(count, 0, f"group {group_index} should be empty")


class TestWiiDiscBuilderNextOffset(unittest.TestCase):

    def test_first_partition_at_0xF800000(self):
        """With no prior partitions, offset must be 0xF800000"""
        builder = WiiDiscBuilder(DiscHeader(), b'\x00' * 0x20)
        self.assertFalse(builder._partitions)
        out = BytesIO(b'\xAA' * 0x50000)
        builder.finish(out)
        out.seek(0x40020)
        self.assertEqual(out.read(4), b'\xAA\xAA\xAA\xAA')


if __name__ == "__main__":
    unittest.main()
