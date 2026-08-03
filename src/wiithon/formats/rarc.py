from io import BytesIO
from typing import BinaryIO, List
import os
from enum import IntFlag

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.exceptions import InvalidFormatError, ArchiveFileNotFoundError, ArchiveEntryExistsError

RARC_MAGIC_WORD: bytes = b'RARC'

class NodeAttribute(IntFlag):
    FILE = 0x01
    DIRECTORY = 0x02
    COMPRESSED = 0x04
    PRELOAD_TO_MRAM = 0x10
    PRELOAD_TO_ARAM = 0x20
    LOAD_FROM_DVD = 0x40
    YAZO_COMPRESSED = 0x80

class RarcNode:
    def __init__(self):
        self.type: str = ""
        self.name_offset: int = 0
        self.name_hash: int = 0
        self.entry_count: int = 0
        self.first_entry_index: int = 0
        self.name: str = ""


class RarcFileEntry:
    def __init__(self):
        self.file_id: int = 0
        self.name_hash: int = 0
        self.attributes: int = 0
        self.name_offset: int = 0
        self.data_offset_or_idx: int = 0
        self.data_size: int = 0
        self.padding: int = 0
        self.name: str = ""
        self._data: bytes = b""

    @property
    def data(self) -> bytes:
        return self._data

    @data.setter
    def data(self, value: bytes) -> None:
        self._data = value
        self.data_size = len(self._data)


class Rarc:
    def __init__(self):
        # Header
        self.base_offset: int = 0
        self.magic_word: bytes = b""
        self.file_length: int = 0
        self.data_offset: int = 0
        self.data_length: int = 0

        # Info block
        self.number_nodes: int = 0
        self.offset_first_node: int = 0
        self.total_directory: int = 0
        self.offset_first_directory: int = 0
        self.string_table_length: int = 0
        self.string_table_offset: int = 0
        self.number_of_files: int = 0

        self.nodes: List[RarcNode] = []
        self.entries: List[RarcFileEntry] = []
        self.string_table: bytes = b""

    @staticmethod
    def _decode_cstring(table: bytes, offset: int) -> str:
        end = table.find(b'\x00', offset)
        raw = table[offset:end] if end != -1 else table[offset:]
        return raw.decode('utf-8', errors='ignore')

    @staticmethod
    def compute_hash(name: str) -> int:
        h = 0
        for c in name:
            h = (h * 3) + ord(c)
            h &= 0xFFFF
        return h

    @classmethod
    def create_empty(cls) -> "Rarc":
        obj = cls()
        root = RarcNode()
        root.type = "ROOT"
        root.name = "ROOT"
        root.first_entry_index = 0
        root.entry_count = 2
        obj.nodes.append(root)

        dot = RarcFileEntry()
        dot.file_id = 0xFFFF
        dot.attributes |= NodeAttribute.DIRECTORY
        dot.name = "."
        dot.data_offset_or_idx = 0

        dotdot = RarcFileEntry()
        dotdot.file_id = 0xFFFFFFFF # Top most directory
        dotdot.attributes |= NodeAttribute.DIRECTORY
        dotdot.name = ".."
        dotdot.data_offset_or_idx = 0

        obj.entries.append(dot)
        obj.entries.append(dotdot)
        return obj

    @classmethod
    def read(cls, stream: BinaryIO) -> "Rarc":
        obj = cls()
        reader = BinaryReader(stream)
        obj.base_offset = reader.tell()

        obj.magic_word = reader.raw(0x04)
        if obj.magic_word != RARC_MAGIC_WORD:
            raise InvalidFormatError("Trying to read a non-rarc file with the rarc struct")

        obj.file_length = reader.u32()
        reader.skip(0x04) # Length of header, always 0x20

        obj.data_offset = reader.u32()
        obj.data_length = reader.u32()
        reader.skip(0xC)
        
        info_block_pos = reader.tell()

        obj.number_nodes = reader.u32()
        obj.offset_first_node = reader.u32()
        obj.total_directory = reader.u32()
        obj.offset_first_directory = reader.u32()
        obj.string_table_length = reader.u32()
        obj.string_table_offset = reader.u32()
        obj.number_of_files = reader.u16()

        reader.skip(0x02 + 0x04)

        # Read nodes
        reader.seek(info_block_pos + obj.offset_first_node)
        for _ in range(obj.number_nodes):
            node = RarcNode()
            node.type = reader.string(0x04)
            node.name_offset = reader.u32()
            node.name_hash = reader.u16()
            node.entry_count = reader.u16()
            node.first_entry_index = reader.u32()
            obj.nodes.append(node)

        # Read file entries
        reader.seek(info_block_pos + obj.offset_first_directory)
        for _ in range(obj.total_directory):
            entry = RarcFileEntry()
            entry.file_id = reader.u16()
            entry.name_hash = reader.u16()
            entry.attributes = reader.u8()
            reader.skip(0x01)
            entry.name_offset = reader.u16()
            entry.data_offset_or_idx = reader.u32()
            entry.data_size = reader.u32()
            entry.padding = reader.u32()
            obj.entries.append(entry)

        # Read string table
        reader.seek(info_block_pos + obj.string_table_offset)
        obj.string_table = reader.raw(obj.string_table_length)

        # Resolve names and read data
        for node in obj.nodes:
            node.name = cls._decode_cstring(obj.string_table, node.name_offset)

        for entry in obj.entries:
            entry.name = cls._decode_cstring(obj.string_table, entry.name_offset)

            if entry.file_id != 0xFFFF and not entry.attributes & NodeAttribute.DIRECTORY:
                abs_data_offset = obj.base_offset + 0x20 + obj.data_offset + entry.data_offset_or_idx
                current_pos = reader.tell()
                reader.seek(abs_data_offset)
                entry.data = reader.raw(entry.data_size)
                reader.seek(current_pos)

        reader.seek(obj.base_offset + obj.file_length)
        return obj

    def extract_to(self, output_dir: str):
        if not self.nodes:
            return
        
        self._extract_node(self.nodes[0], output_dir)

    def _extract_node(self, node: RarcNode, current_dir: str):
        os.makedirs(current_dir, exist_ok=True)

        for i in range(node.entry_count):
            entry = self.entries[node.first_entry_index + i]

            if entry.name in (".", ".."):
                continue

            path = os.path.join(current_dir, entry.name)

            if entry.file_id == 0xFFFF or entry.attributes & NodeAttribute.DIRECTORY:
                # Subdirectory
                child_node = self.nodes[entry.data_offset_or_idx]
                self._extract_node(child_node, path)
            else:
                # File
                with open(path, "wb") as f:
                    f.write(entry.data)
                    
    def write(self, stream: BinaryIO):
        string_table_bytes = bytearray()
        string_map = {}
        writer = BinaryWriter(stream)
        
        def add_string(name: str) -> int:
            if name in string_map:
                return string_map[name]
            offset = len(string_table_bytes)
            string_map[name] = offset
            string_table_bytes.extend(name.encode('utf-8') + b'\x00')
            return offset
            
        # Pack nodes
        for node in self.nodes:
            node_name = node.name or node.type.strip('\x00')
            node.name_offset = add_string(node_name)
            node.name_hash = self.compute_hash(node_name)

        # Pack entries
        for entry in self.entries:
            entry.name_offset = add_string(entry.name)
            entry.name_hash = self.compute_hash(entry.name)

        # Assign sequential file ids to real files, 0xFFFF for directories
        file_id_counter = 0
        for entry in self.entries:
            if entry.attributes & NodeAttribute.DIRECTORY:
                entry.file_id = 0xFFFF
            else:
                entry.file_id = file_id_counter
                file_id_counter += 1

        # align string table to 0x20
        while len(string_table_bytes) % 0x20 != 0:
            string_table_bytes.append(0x00)

        self.string_table = bytes(string_table_bytes)
        self.string_table_length = len(self.string_table)

        self.number_nodes = len(self.nodes)
        self.total_directory = len(self.entries)

        # Sizes
        nodes_size = self.number_nodes * 0x10
        entries_size = self.total_directory * 0x14
        
        self.offset_first_node = 0x20
        self.offset_first_directory = self.offset_first_node + nodes_size
        self.string_table_offset = self.offset_first_directory + entries_size
        
        # Calculate data offsets and payloads
        payload = bytearray()
        for entry in self.entries:
            if entry.file_id != 0xFFFF and not entry.attributes & NodeAttribute.DIRECTORY:
                # Align payload to 0x20
                while len(payload) % 0x20 != 0:
                    payload.append(0x00)
                entry.data_offset_or_idx = len(payload)
                entry.data_size = len(entry.data)
                payload.extend(entry.data)

        # Align end of payload
        while len(payload) % 0x20 != 0:
            payload.append(0x00)

        self.data_offset = self.string_table_offset + self.string_table_length
        self.data_length = len(payload)
        self.file_length = 0x40 + self.string_table_offset + self.string_table_length + self.data_length

        # Header
        writer.raw(RARC_MAGIC_WORD)
        writer.u32(self.file_length)
        writer.u32(0x20)
        writer.u32(self.data_offset)
        writer.u32(self.data_length)
        writer.pad(0x0C)

        # Info block (at 0x20)
        writer.u32(self.number_nodes)
        writer.u32(self.offset_first_node)
        writer.u32(self.total_directory)
        writer.u32(self.offset_first_directory)
        writer.u32(self.string_table_length)
        writer.u32(self.string_table_offset)

        writer.u16(file_id_counter)
        writer.pad(0x06)

        # Nodes
        for node in self.nodes:
            writer.string(node.type, 0x04, encoding='ascii')
            writer.u32(node.name_offset)
            writer.u16(node.name_hash)
            writer.u16(node.entry_count)
            writer.u32(node.first_entry_index)

        # Entries
        for entry in self.entries:
            writer.u16(entry.file_id)
            writer.u16(entry.name_hash)
            writer.u8(entry.attributes)
            writer.u8(0)
            writer.u16(entry.name_offset)
            writer.u32(entry.data_offset_or_idx)
            writer.u32(entry.data_size)
            writer.u32(0)

        # String table
        writer.raw(self.string_table)

        # Data payload
        writer.raw(payload)

    def get_file(self, name: str) -> RarcFileEntry:
        for entry in self.entries:
            if entry.name == name and entry.file_id != 0xFFFF and not entry.attributes & NodeAttribute.DIRECTORY:
                return entry

        raise ArchiveFileNotFoundError(f"File not found in RARC: {name}")

    def replace_file(self, name: str, data: bytes) -> None:
        for entry in self.entries:
            if entry.name == name and entry.file_id != 0xFFFF and not entry.attributes & NodeAttribute.DIRECTORY:
                entry.data = data
                return

        raise ArchiveFileNotFoundError(f"File not found in RARC: {name}")

    def _find_node_for_path(self, parts: list[str]) -> RarcNode:
        node = self.nodes[0]  # root
        if parts and parts[0] == node.name:
            parts = parts[1:]
        for part in parts:
            found = False
            for i in range(node.entry_count):
                entry = self.entries[node.first_entry_index + i]
                if entry.name == part and entry.attributes & NodeAttribute.DIRECTORY:  # répertoire
                    node = self.nodes[entry.data_offset_or_idx]
                    found = True
                    break
            if not found:
                raise ArchiveFileNotFoundError(f"Directory not found in RARC: {part}")
        return node

    def _has_sibling_named(self, node: RarcNode, name: str) -> bool:
        return any(
            self.entries[node.first_entry_index + i].name == name
            for i in range(node.entry_count)
        )

    def _insert_entry(self, node: RarcNode, entry: RarcFileEntry) -> None:
        pos = node.first_entry_index + node.entry_count
        self.entries.insert(pos, entry)
        node.entry_count += 1
        for other in self.nodes:
            if other is not node and other.first_entry_index >= pos:
                other.first_entry_index += 1

    def add_node(self, path: str) -> RarcNode:
        parts = [p for p in path.split("/") if p]
        if not parts:
            raise ValueError(f"Path must contain a directory name: {path}")

        parent_node = self._find_node_for_path(parts[:-1])
        name = parts[-1]
        if self._has_sibling_named(parent_node, name):
            raise ArchiveEntryExistsError(f"'{name}' already exists in this directory")
        parent_index = self.nodes.index(parent_node)

        new_node = RarcNode()
        new_node.type = name[:4].upper().ljust(4)
        new_node.name = name
        new_node_index = len(self.nodes)
        new_node.first_entry_index = len(self.entries)

        dot_entry = RarcFileEntry()
        dot_entry.file_id = 0xFFFF
        dot_entry.attributes |= NodeAttribute.DIRECTORY
        dot_entry.name = "."
        dot_entry.data_offset_or_idx = new_node_index

        dotdot_entry = RarcFileEntry()
        dotdot_entry.file_id = 0xFFFF
        dotdot_entry.attributes |= NodeAttribute.DIRECTORY
        dotdot_entry.name = ".."
        dotdot_entry.data_offset_or_idx = parent_index

        self.entries.append(dot_entry)
        self.entries.append(dotdot_entry)
        new_node.entry_count = 2
        self.nodes.append(new_node)

        dir_entry = RarcFileEntry()
        dir_entry.file_id = 0xFFFF
        dir_entry.attributes |= NodeAttribute.DIRECTORY
        dir_entry.name = name
        dir_entry.data_offset_or_idx = new_node_index
        self._insert_entry(parent_node, dir_entry)

        return new_node

    def add_file(self, path: str, data: bytes) -> RarcFileEntry:
        parts = [p for p in path.split("/") if p]
        if not parts:
            raise ValueError("Path must contain a file name")

        node = self._find_node_for_path(parts[:-1])
        name = parts[-1]
        if self._has_sibling_named(node, name):
            raise ArchiveEntryExistsError(f"'{name}' already exists in this directory")

        entry = RarcFileEntry()
         # TODO Test whether both attributes are required or simply having FILE is sufficient
        entry.attributes |= NodeAttribute.FILE | NodeAttribute.PRELOAD_TO_MRAM
        entry.name = name
        entry.data = data
        self._insert_entry(node, entry)

        return entry

    def rename_file(self, path: str, new_name: str, data: bytes = None) -> RarcFileEntry:
        parts = [p for p in path.split("/") if p]
        if not parts:
            raise ValueError("Path must contain a file name")

        node = self._find_node_for_path(parts[:-1])
        old_name = parts[-1]

        entry = None
        for i in range(node.entry_count):
            candidate = self.entries[node.first_entry_index + i]
            if candidate.name == old_name and candidate.file_id != 0xFFFF and not candidate.attributes & NodeAttribute.DIRECTORY:
                entry = candidate
                break
        if entry is None:
            raise ArchiveFileNotFoundError(f"File not found in RARC: {path}")

        if new_name != old_name and self._has_sibling_named(node, new_name):
            raise ArchiveEntryExistsError(f"'{new_name}' already exists in this directory")

        entry.name = new_name
        if data is not None:
            entry.data = data

        return entry

    def get_file_by_path(self, path: str) -> RarcFileEntry:
        parts = [p for p in path.split("/") if p]
        node = self._find_node_for_path(parts[:-1])
        filename = parts[-1]

        for i in range(node.entry_count):
            entry = self.entries[node.first_entry_index + i]
            if entry.name != filename:
                continue
            if not entry.attributes & NodeAttribute.DIRECTORY:
                return entry

            sub_node = self.nodes[entry.data_offset_or_idx]
            files = [
                self.entries[sub_node.first_entry_index + j]
                for j in range(sub_node.entry_count)
                if self.entries[sub_node.first_entry_index + j].name not in (".", "..")
                and not self.entries[sub_node.first_entry_index + j].attributes & NodeAttribute.DIRECTORY
            ]
            if len(files) == 1:
                return files[0]
            names = ", ".join(e.name for e in files)
            raise ValueError(
                f"'{filename}' is a directory with {len(files)} files called : {names}"
            )

        raise ArchiveFileNotFoundError(f"File not found: {path}")

    def replace_file_by_path(self, path: str, data: bytes) -> None:
        parts = [p for p in path.split("/") if p]
        node = self._find_node_for_path(parts[:-1])
        filename = parts[-1]
        for i in range(node.entry_count):
            entry = self.entries[node.first_entry_index + i]
            if entry.name == filename and not entry.attributes & NodeAttribute.DIRECTORY:
                entry.data = data
                return
        raise ArchiveFileNotFoundError(f"File not found: {path}")

    def get_bytes(self) -> bytes:
        buffer = BytesIO()
        self.write(buffer)
        return buffer.getvalue()