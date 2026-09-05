import os
import struct
import tempfile
import unittest
from io import BytesIO

from wiithon.exceptions import ArchiveEntryExistsError, ArchiveFileNotFoundError
from wiithon.formats.rarc import NodeAttribute, Rarc, RarcFileEntry

HEADER_SIZE = 0x20
INFO_SIZE = 0x20
NODE_SIZE = 0x10
ENTRY_SIZE = 0x14
ALIGNMENT = 0x20


def _entry(file_id: int, entry_type: int, name_offset: int, data_offset: int, size: int) -> bytes:
    return struct.pack(">HHIIII", file_id, 0, (entry_type << 24) | name_offset, data_offset, size, 0)


def build_mock_rarc() -> bytes:
    strings = b"ROOT\0.\0file.txt\0"
    data = b"Hello World !"

    first_node = INFO_SIZE
    first_entry = first_node + NODE_SIZE
    string_table = first_entry + 2 * ENTRY_SIZE
    data_offset = string_table + len(strings)

    info = struct.pack(">IIIIIIHHI", 1, first_node, 2, first_entry, len(strings), string_table, 1, 0, 0)
    root = struct.pack(">4sIHHI", b"ROOT", 0, 0, 2, 0)
    entries = _entry(0xFFFF, 0x02, 5, 0, 0x10) + _entry(0, 0x11, 7, 0, len(data))

    body = info + root + entries + strings + data
    header = struct.pack(">4sIIIIIII", b"RARC", HEADER_SIZE + len(body), HEADER_SIZE, data_offset, len(data), 0, 0, 0)
    return header + body


def build_named_root_rarc() -> bytes:
    strings = b"stage\0.\0..\0files\0example.txt\0"
    strings += b"\0" * (-len(strings) % ALIGNMENT)
    stage_off, dot_off, dotdot_off, files_off, example_off = 0, 6, 8, 11, 17

    data = b"hi"
    node_count, entry_count = 2, 6
    first_node = INFO_SIZE
    first_entry = first_node + node_count * NODE_SIZE
    string_table = first_entry + entry_count * ENTRY_SIZE
    data_offset = string_table + len(strings)

    info = struct.pack(
        ">IIIIIIHHI", node_count, first_node, entry_count, first_entry, len(strings), string_table, 1, 0, 0
    )
    nodes = struct.pack(">4sIHHI", b"ROOT", stage_off, 0, 3, 0) + struct.pack(">4sIHHI", b"FILE", files_off, 0, 3, 3)

    entries = b"".join((
        _entry(0xFFFF, 0x02, dot_off, 0, 0),
        _entry(0xFFFF, 0x02, dotdot_off, 0, 0),
        _entry(0xFFFF, 0x02, files_off, 1, 0),
        _entry(0xFFFF, 0x02, dot_off, 1, 0),
        _entry(0xFFFF, 0x02, dotdot_off, 0, 0),
        _entry(0, 0x11, example_off, 0, len(data)),
    ))

    body = info + nodes + entries + strings + data
    header = struct.pack(">4sIIIIIII", b"RARC", HEADER_SIZE + len(body), HEADER_SIZE, data_offset, len(data), 0, 0, 0)
    return header + body


def named_root_rarc() -> Rarc:
    return Rarc.read(BytesIO(build_named_root_rarc()))


def build_nested_rarc() -> Rarc:
    arc = Rarc.create_empty()
    arc.nodes[0].name = "stage"
    arc.add_node("stage/files")
    arc.add_node("stage/files/deep")
    arc.add_file("stage/root.bdl", b"R" * 40)
    arc.add_file("stage/files/nested.bin", b"N" * 7)
    arc.add_file("stage/files/deep/empty.txt", b"")
    return arc


def reloaded(rarc: Rarc) -> Rarc:
    out = BytesIO()
    rarc.write(out)
    out.seek(0)
    return Rarc.read(out)


class TestRarc(unittest.TestCase):
    def test_roundtrip_is_byte_stable(self):
        once = build_nested_rarc().get_bytes()
        twice = Rarc.read(BytesIO(once)).get_bytes()
        thrice = Rarc.read(BytesIO(twice)).get_bytes()

        self.assertEqual(once, twice)
        self.assertEqual(twice, thrice)

    def test_roundtrip_keeps_the_tree_and_the_data(self):
        source = build_nested_rarc()
        copy = reloaded(source)

        self.assertEqual([node.name for node in copy.nodes], [node.name for node in source.nodes])
        self.assertEqual([entry.name for entry in copy.entries], [entry.name for entry in source.entries])

        for path in ("stage/root.bdl", "stage/files/nested.bin", "stage/files/deep/empty.txt"):
            self.assertEqual(copy.get_file(path).data, source.get_file(path).data, path)

    def test_roundtrip_keeps_parent_links_resolvable(self):
        copy = reloaded(build_nested_rarc())

        deep = copy.get_node("stage/files/deep")
        parent = copy.entries[deep.first_entry_index + 1]

        self.assertEqual(parent.name, "..")
        self.assertEqual(copy.nodes[parent.data_offset_or_idx].name, "files")
        self.assertTrue(parent.attributes & NodeAttribute.DIRECTORY)

    def test_root_keeps_a_name_of_its_own(self):
        rarc = named_root_rarc()
        self.assertEqual(rarc.nodes[0].type, "ROOT")
        self.assertEqual(rarc.nodes[0].name, "stage")

        copy = reloaded(rarc)
        self.assertEqual(copy.nodes[0].type, "ROOT")
        self.assertEqual(copy.nodes[0].name, "stage")
        self.assertEqual(copy.get_file("stage/files/example.txt").data, b"hi")

    def test_a_path_may_start_above_or_below_the_root(self):
        rarc = named_root_rarc()

        self.assertEqual(rarc.get_file("stage/files/example.txt").data, b"hi")
        self.assertEqual(rarc.get_file("files/example.txt").data, b"hi")

    def test_an_empty_path_means_the_root(self):
        rarc = Rarc.create_empty()
        self.assertIs(rarc.get_node(""), rarc.nodes[0])
        self.assertIs(rarc.get_node("/"), rarc.nodes[0])
        with self.assertRaises(ValueError):
            rarc.get_node(None)

        named = named_root_rarc()
        self.assertIs(named.get_node("stage"), named.nodes[0])

    def test_get_node_walks_the_tree(self):
        rarc = Rarc.create_empty()
        sub = rarc.add_node("sub")
        self.assertIs(rarc.get_node("/sub"), sub)

        self.assertEqual(named_root_rarc().get_node("stage/files").name, "files")

    def test_unknown_directories_are_reported(self):
        with self.assertRaises(ArchiveFileNotFoundError):
            named_root_rarc().get_node("bogus")

        rarc = Rarc.create_empty()
        rarc.add_node("sub")
        with self.assertRaises(ArchiveFileNotFoundError):
            rarc.get_node("sub/missing")

    def test_reads_a_hand_written_archive(self):
        rarc = Rarc.read(BytesIO(build_mock_rarc()))

        self.assertEqual(rarc.magic_word, b"RARC")
        self.assertEqual(rarc.number_nodes, 1)
        self.assertEqual(rarc.total_directory, 2)
        self.assertEqual(rarc.nodes[0].type, "ROOT")
        self.assertEqual(rarc.entries[1].name, "file.txt")
        self.assertEqual(rarc.entries[1].data_size, 0xD)

    def test_extracts_its_files_to_disk(self):
        rarc = Rarc.read(BytesIO(build_mock_rarc()))

        with tempfile.TemporaryDirectory() as tmpdir:
            rarc.extract_to(tmpdir)

            extracted = os.path.join(tmpdir, "file.txt")
            self.assertTrue(os.path.exists(extracted), "Extracted file should exist")
            with open(extracted, "rb") as handle:
                self.assertEqual(handle.read(), b"Hello World !")

    def test_writes_back_a_modified_entry(self):
        """Changing the payload must not disturb the tree around it"""
        rarc = Rarc.read(BytesIO(build_mock_rarc()))
        rarc.entries[1].data = b"Apagnan"

        copy = reloaded(rarc)
        self.assertEqual(len(copy.nodes), 1)
        self.assertEqual(len(copy.entries), 2)
        self.assertEqual(copy.entries[1].name, "file.txt")
        self.assertEqual(copy.entries[1].data, b"Apagnan")

    def test_a_fresh_archive_holds_only_its_dot_entries(self):
        rarc = Rarc.create_empty()

        self.assertEqual(len(rarc.nodes), 1)
        self.assertEqual(rarc.nodes[0].type, "ROOT")
        self.assertEqual(rarc.nodes[0].entry_count, 2)
        self.assertEqual([entry.name for entry in rarc.entries], [".", ".."])

        copy = reloaded(rarc)
        self.assertEqual(len(copy.nodes), 1)
        self.assertEqual(copy.nodes[0].type, "ROOT")

    def test_add_file_lands_in_the_root(self):
        rarc = Rarc.create_empty()
        entry = rarc.add_file("hello.txt", b"Hello World!")

        self.assertIsInstance(entry, RarcFileEntry)
        self.assertEqual(entry.name, "hello.txt")
        self.assertEqual(entry.data, b"Hello World!")

        copy = reloaded(rarc)
        self.assertEqual(copy.get_file("hello.txt").data, b"Hello World!")
        self.assertEqual(copy.nodes[0].entry_count, 3)

    def test_add_node_creates_a_subdirectory(self):
        rarc = Rarc.create_empty()
        sub_node = rarc.add_node("sub")

        self.assertEqual(len(rarc.nodes), 2)
        self.assertIs(rarc.nodes[1], sub_node)
        self.assertEqual(sub_node.type, "SUB ")
        self.assertEqual(sub_node.entry_count, 2)
        self.assertEqual([e.name for e in rarc.entries], [".", "..", "sub", ".", ".."])

        copy = reloaded(rarc)
        self.assertEqual(len(copy.nodes), 2)
        self.assertEqual(copy.nodes[1].type, "SUB ")

    def test_add_file_after_a_node_keeps_both_blocks_intact(self):
        rarc = Rarc.create_empty()
        rarc.add_node("sub")
        rarc.add_file("sub/inner.txt", b"Inner data")
        rarc.add_file("second.txt", b"second")

        copy = reloaded(rarc)
        self.assertEqual(copy.get_file("second.txt").data, b"second")
        self.assertEqual(copy.get_file("sub/inner.txt").data, b"Inner data")

    def test_add_node_unknown_parent(self):
        rarc = Rarc.create_empty()
        with self.assertRaises(ArchiveFileNotFoundError):
            rarc.add_node("missing/sub")

    def test_names_only_clash_inside_the_same_folder(self):
        """JAAAAAAAAKE"""
        rarc = Rarc.create_empty()
        rarc.add_node("Jake")
        rarc.add_node("Ekaj")
        rarc.add_node("other")

        with self.assertRaises(ArchiveEntryExistsError):
            rarc.add_node("Jake")

        self.assertEqual(rarc.add_node("other/Jake").type, "JAKE")

    def test_a_file_cannot_take_a_name_already_used(self):
        rarc = Rarc.create_empty()
        rarc.add_node("data")
        rarc.add_file("hello.txt", b"one")

        with self.assertRaises(ArchiveEntryExistsError):
            rarc.add_file("hello.txt", b"two")
        with self.assertRaises(ArchiveEntryExistsError):
            rarc.add_file("data", b"oops")

    def test_the_same_file_name_lives_in_two_folders(self):
        rarc = Rarc.create_empty()
        rarc.add_node("sub")
        rarc.add_file("hello.txt", b"root version")
        rarc.add_file("sub/hello.txt", b"sub version")

        copy = reloaded(rarc)
        self.assertEqual(copy.get_file("hello.txt").data, b"root version")
        self.assertEqual(copy.get_file("sub/hello.txt").data, b"sub version")

    def test_replace_file_swaps_the_data(self):
        rarc = Rarc.create_empty()
        rarc.add_file("hello.txt", b"old data")

        rarc.replace_file("hello.txt", b"new data")
        self.assertEqual(rarc.get_file("hello.txt").data, b"new data")

        rarc.replace_file("hello.txt", b"newer data")
        self.assertEqual(rarc.get_file("hello.txt").data, b"newer data")

    def test_replace_file_can_rename_on_the_way(self):
        rarc = Rarc.create_empty()
        rarc.add_node("sub")
        rarc.add_file("hello.txt", b"Hello World!")
        rarc.add_file("sub/inner.txt", b"data")

        rarc.replace_file("hello.txt", b"new data", new_name="greeting.txt")
        rarc.replace_file("sub/inner.txt", b"new data", new_name="renamed.txt")

        with self.assertRaises(ArchiveFileNotFoundError):
            rarc.get_file("hello.txt")

        copy = reloaded(rarc)
        self.assertEqual(copy.get_file("greeting.txt").data, b"new data")
        self.assertEqual(copy.get_file("sub/renamed.txt").data, b"new data")

    def test_a_rename_stays_inside_its_folder(self):
        rarc = Rarc.create_empty()
        rarc.add_file("a.txt", b"a")
        rarc.add_file("b.txt", b"b")

        with self.assertRaises(ValueError):
            rarc.replace_file("a.txt", b"a", new_name="sub/renamed.txt")
        with self.assertRaises(ArchiveEntryExistsError):
            rarc.replace_file("a.txt", b"aa", new_name="b.txt")

        rarc.replace_file("a.txt", b"aa", new_name="a.txt")
        self.assertEqual(rarc.get_file("a.txt").data, b"aa")

    def test_replace_file_not_found(self):
        rarc = Rarc.create_empty()
        with self.assertRaises(ArchiveFileNotFoundError):
            rarc.replace_file("missing.txt", b"data")

    def test_the_root_is_empty_until_something_is_added(self):
        rarc = Rarc.create_empty()
        self.assertTrue(rarc.is_node_empty(""))

        rarc.add_file("hello.txt", b"data")
        self.assertFalse(rarc.is_node_empty(""))

    def test_a_fresh_subdirectory_is_empty(self):
        rarc = Rarc.create_empty()
        rarc.add_node("sub")

        self.assertFalse(rarc.is_node_empty(""))
        self.assertTrue(rarc.is_node_empty("/sub"))

        rarc.add_file("sub/inner.txt", b"data")
        self.assertFalse(rarc.is_node_empty("/sub"))

    def test_remove_file_drops_the_entry(self):
        rarc = Rarc.create_empty()
        rarc.add_file("hello.txt", b"data")

        rarc.remove_file("hello.txt")

        with self.assertRaises(ArchiveFileNotFoundError):
            rarc.get_file("hello.txt")
        self.assertEqual(rarc.nodes[0].entry_count, 2)

    def test_remove_file_leaves_the_siblings_intact(self):
        rarc = Rarc.create_empty()
        rarc.add_node("sub")
        rarc.add_file("sub/a.txt", b"a")
        rarc.add_file("sub/b.txt", b"b")

        rarc.remove_file("sub/a.txt")

        copy = reloaded(rarc)
        self.assertEqual(copy.get_file("sub/b.txt").data, b"b")
        with self.assertRaises(ArchiveFileNotFoundError):
            copy.get_file("sub/a.txt")

    def test_remove_file_refuses_what_is_not_a_file(self):
        rarc = Rarc.create_empty()
        rarc.add_node("sub")

        with self.assertRaises(ArchiveFileNotFoundError):
            rarc.remove_file("missing.txt")
        with self.assertRaises(ValueError):
            rarc.remove_file("sub")

    def test_remove_node_deletes_an_empty_subdirectory(self):
        rarc = Rarc.create_empty()
        rarc.add_node("sub")

        rarc.remove_node("/sub")

        self.assertEqual(len(rarc.nodes), 1)
        self.assertTrue(rarc.is_node_empty(""))
        self.assertEqual(len(reloaded(rarc).nodes), 1)

    def test_remove_node_takes_its_children_with_it(self):
        rarc = Rarc.create_empty()
        rarc.add_node("sub")
        rarc.add_node("sub/nested")
        rarc.add_file("sub/nested/deep.txt", b"deep")
        rarc.add_file("root.txt", b"root")

        rarc.remove_node("/sub")

        self.assertEqual(len(rarc.nodes), 1)
        self.assertEqual(rarc.nodes[0].entry_count, 3)  # ".", "..", "root.txt"

        copy = reloaded(rarc)
        self.assertEqual(len(copy.nodes), 1)
        self.assertEqual(copy.get_file("root.txt").data, b"root")
        with self.assertRaises(ArchiveFileNotFoundError):
            copy.get_node("/sub")

    def test_remove_node_survives_the_root_dotdot_sentinel(self):
        rarc = Rarc.create_empty()
        rarc.entries[1].data_offset_or_idx = 0xFFFFFFFF
        rarc.add_node("sub")

        rarc.remove_node("/sub")

        self.assertEqual(len(rarc.nodes), 1)
        self.assertEqual(rarc.entries[1].data_offset_or_idx, 0xFFFFFFFF)

    def test_remove_node_refuses_the_root_and_the_unknown(self):
        rarc = Rarc.create_empty()

        with self.assertRaises(ValueError):
            rarc.remove_node("")
        with self.assertRaises(ArchiveFileNotFoundError):
            rarc.remove_node("/missing")

    def test_a_node_can_be_added_back_after_a_removal(self):
        rarc = Rarc.create_empty()
        rarc.add_node("sub")
        rarc.remove_node("/sub")
        rarc.add_node("sub2")

        copy = reloaded(rarc)
        self.assertEqual(len(copy.nodes), 2)
        self.assertEqual(copy.nodes[1].type, "SUB2")


class TestRarcHeaderLayout(unittest.TestCase):

    def setUp(self):
        self.arc = build_nested_rarc()
        self.raw = self.arc.get_bytes()

        self.magic, self.file_length, self.header_length, self.data_offset, self.data_length = struct.unpack(
            ">4sIIII", self.raw[:0x14]
        )
        (
            self.number_nodes,
            self.offset_first_node,
            self.total_directory,
            self.offset_first_directory,
            self.string_table_length,
            self.string_table_offset,
            self.number_of_files,
        ) = struct.unpack(">6IH", self.raw[HEADER_SIZE:HEADER_SIZE + 0x1A])

    def test_magic_and_header_length(self):
        self.assertEqual(self.magic, b"RARC")
        self.assertEqual(self.header_length, HEADER_SIZE)

    def test_file_length_matches_written_size(self):
        self.assertEqual(self.file_length, len(self.raw))

    def test_data_section_ends_at_end_of_file(self):
        self.assertEqual(HEADER_SIZE + self.data_offset + self.data_length, len(self.raw))

    def test_section_offsets_are_contiguous(self):
        self.assertEqual(self.offset_first_node, HEADER_SIZE)
        self.assertEqual(self.offset_first_directory, self.offset_first_node + self.number_nodes * NODE_SIZE)
        self.assertEqual(self.string_table_offset, self.offset_first_directory + self.total_directory * ENTRY_SIZE)
        self.assertEqual(self.data_offset, self.string_table_offset + self.string_table_length)

    def test_counts_match_the_archive(self):
        self.assertEqual(self.number_nodes, len(self.arc.nodes))
        self.assertEqual(self.total_directory, len(self.arc.entries))
        self.assertEqual(self.number_of_files, 3)

    def test_string_table_and_data_are_aligned(self):
        self.assertEqual(self.string_table_length % ALIGNMENT, 0)
        self.assertEqual(self.data_length % ALIGNMENT, 0)

    def test_root_node_is_readable_at_its_announced_offset(self):
        start = HEADER_SIZE + self.offset_first_node
        node_type, name_offset, _, entry_count, first_entry_index = struct.unpack(
            ">4sIHHI", self.raw[start:start + NODE_SIZE]
        )
        table = self.raw[HEADER_SIZE + self.string_table_offset:][:self.string_table_length]

        self.assertEqual(node_type, b"ROOT")
        self.assertEqual(table[name_offset:table.index(b"\0", name_offset)], b"stage")
        self.assertEqual(entry_count, self.arc.nodes[0].entry_count)
        self.assertEqual(first_entry_index, 0)

    def test_read_stops_at_the_end_of_the_archive(self):
        sentinel = b"STOOOOP"
        stream = BytesIO(self.raw + sentinel)

        Rarc.read(stream)

        self.assertEqual(stream.tell(), len(self.raw))
        self.assertEqual(stream.read(), sentinel)

if __name__ == "__main__":
    unittest.main()