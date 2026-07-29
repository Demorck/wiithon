import os

import unittest
from io import BytesIO
import struct
import tempfile

from wiithon.formats.rarc import Rarc
from wiithon.exceptions import ArchiveFileNotFoundError

class TestRarc(unittest.TestCase):
    def build_mock_rarc(self) -> bytes:
        # Building the RARC header (0x20 bytes)
        magic = b'RARC'
        file_length = 0x20 + 0x20 + 0x10 + (2 * 0x14) + 0x10 + 0x10 # estimation
        header_len = 0x20
        data_offset = 0x10 + 0x28 + 0x10
        data_offset = 0x68
        data_length = 0x0D # "Hello World !"
        
        header = struct.pack(">4sIIIIIII", magic, file_length, header_len, data_offset, data_length, 0, 0, 0)

        number_nodes = 1
        offset_first_node = 0x20
        total_directory = 2
        offset_first_directory = 0x20 + 0x10
        string_table_length = 16
        string_table_offset = 0x20 + 0x10 + 0x28
        number_of_files = 1
        info_block = struct.pack(">IIIIIIHHI", number_nodes, offset_first_node, total_directory, offset_first_directory,
                                 string_table_length, string_table_offset, number_of_files, 0, 0)
        
        # Node 1 (Root, 0x10 bytes)
        node1 = struct.pack(">4sIHHI", b'ROOT', 0, 0, 2, 0)
        
        # Entries (0x28 bytes)
        # Entry 1: "."
        entry1_attr = (0x02 << 24) | 0x05
        entry1 = struct.pack(">HHIIII", 0xFFFF, 0, entry1_attr, 0, 0x10, 0)
        
        # Entry 2: "file.txt"
        entry2_attr = (0x11 << 24) | 0x07
        entry2 = struct.pack(">HHIIII", 0, 0, entry2_attr, 0, 0xD, 0)

        strings = b"ROOT\0.\0file.txt\0"

        data = b"Hello World !"
        
        rarc_data = header + info_block + node1 + entry1 + entry2 + strings + data
        rarc_data = rarc_data[:4] + struct.pack(">I", len(rarc_data)) + rarc_data[8:]
        return rarc_data

    def test_read_rarc(self):
        data = self.build_mock_rarc()
        stream = BytesIO(data)
        
        rarc = Rarc.read(stream)
        
        self.assertEqual(rarc.magic_word, b"RARC")
        self.assertEqual(rarc.number_nodes, 1)
        self.assertEqual(rarc.total_directory, 2)
        
        self.assertEqual(rarc.nodes[0].type, "ROOT\0\0\0\0"[:4])
        self.assertEqual(rarc.entries[1].name, "file.txt")
        self.assertEqual(rarc.entries[1].data_size, 0xD)

    def test_extract_to(self):
        data = self.build_mock_rarc()
        stream = BytesIO(data)
        rarc = Rarc.read(stream)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            rarc.extract_to(tmpdir)
            
            filepath = os.path.join(tmpdir, "file.txt")
            self.assertTrue(os.path.exists(filepath), "Extracted file should exist")
            
            with open(filepath, "rb") as f:
                content = f.read()
            self.assertEqual(content, b"Hello World !")

    def test_write_rarc(self):
        data = self.build_mock_rarc()
        stream = BytesIO(data)
        rarc = Rarc.read(stream)

        rarc.entries[1].data = b"Apagnan"
        
        out_stream = BytesIO()
        rarc.write(out_stream)
        
        out_stream.seek(0)
        new_rarc = Rarc.read(out_stream)
        
        self.assertEqual(len(new_rarc.nodes), 1)
        self.assertEqual(len(new_rarc.entries), 2)
        self.assertEqual(new_rarc.entries[1].name, "file.txt")
        self.assertEqual(new_rarc.entries[1].data, b"Apagnan")

    def test_create_empty(self):
        rarc = Rarc.create_empty()

        self.assertEqual(len(rarc.nodes), 1)
        self.assertEqual(rarc.nodes[0].type, "ROOT")
        self.assertEqual(rarc.nodes[0].entry_count, 2)
        self.assertEqual([e.name for e in rarc.entries], [".", ".."])

        out_stream = BytesIO()
        rarc.write(out_stream)
        out_stream.seek(0)
        reloaded = Rarc.read(out_stream)

        self.assertEqual(len(reloaded.nodes), 1)
        self.assertEqual(reloaded.nodes[0].type, "ROOT")

    def test_add_file_to_root(self):
        rarc = Rarc.create_empty()
        rarc.add_file("hello.txt", b"Hello World!")

        out_stream = BytesIO()
        rarc.write(out_stream)
        out_stream.seek(0)
        reloaded = Rarc.read(out_stream)

        self.assertEqual(reloaded.get_file_by_path("hello.txt"), b"Hello World!")
        self.assertEqual(reloaded.nodes[0].entry_count, 3)

    def test_add_node_creates_subdirectory(self):
        rarc = Rarc.create_empty()
        sub_node = rarc.add_node("sub")

        self.assertEqual(len(rarc.nodes), 2)
        self.assertIs(rarc.nodes[1], sub_node)
        self.assertEqual(sub_node.type, "SUB ")
        self.assertEqual(sub_node.entry_count, 2)
        self.assertEqual([e.name for e in rarc.entries], [".", "..", "sub", ".", ".."])

        out_stream = BytesIO()
        rarc.write(out_stream)
        out_stream.seek(0)
        reloaded = Rarc.read(out_stream)

        self.assertEqual(len(reloaded.nodes), 2)
        self.assertEqual(reloaded.nodes[1].type, "SUB ")

    def test_add_file_inside_new_node(self):
        rarc = Rarc.create_empty()
        rarc.add_node("sub")
        rarc.add_file("sub/inner.txt", b"Inner data")

        out_stream = BytesIO()
        rarc.write(out_stream)
        out_stream.seek(0)
        reloaded = Rarc.read(out_stream)

        self.assertEqual(reloaded.get_file_by_path("sub/inner.txt"), b"Inner data")

    def test_add_file_after_node_shifts_indices_correctly(self):
        # Regression check: inserting a file into the root's entry block after a
        # subdirectory's block has been appended must not corrupt either block.
        rarc = Rarc.create_empty()
        rarc.add_node("sub")
        rarc.add_file("sub/inner.txt", b"Inner data")
        rarc.add_file("second.txt", b"second")

        out_stream = BytesIO()
        rarc.write(out_stream)
        out_stream.seek(0)
        reloaded = Rarc.read(out_stream)

        self.assertEqual(reloaded.get_file_by_path("second.txt"), b"second")
        self.assertEqual(reloaded.get_file_by_path("sub/inner.txt"), b"Inner data")

    def test_add_node_unknown_parent_raises(self):
        rarc = Rarc.create_empty()
        with self.assertRaises(ArchiveFileNotFoundError):
            rarc.add_node("missing/sub")

if __name__ == '__main__':
    unittest.main()
