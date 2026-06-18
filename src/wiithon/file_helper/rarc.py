from typing import BinaryIO, List
import os

from wiithon.helpers.Utils import read_string, read_u32, read_u16


class RarcNode:
    """Represents a directory node within a RARC archive"""

    type: str
    """A 4-character string identifying the node type (`FILE`, `DIR`)"""

    name_offset: int
    """Offset of the node name in the string table"""

    name_hash: int
    """Computed hash of the node's name"""

    entry_count: int
    """Number of file/subdirectory entries in this node"""

    first_entry_index: int
    """Index into the entries list where this node starts"""

    def __init__(self):
        self.type: str = ""
        self.name_offset: int = 0
        self.name_hash: int = 0
        self.entry_count: int = 0
        self.first_entry_index: int = 0


class RarcFileEntry:
    """Represents a file or subdirectory entry within a RARC node"""

    file_id: int
    """Unique identifier for the file (0xFFFF indicates a subdirectory)"""

    name_hash: int
    """Computed hash of the entry's name"""

    attributes: int
    """Raw combined attributes (type and name offset)"""

    type: int
    """Type of the entry (0x02 for directories, 0x11 for files)"""

    name_offset: int
    """Offset in the string table for the entry's name"""

    data_offset_or_idx: int
    """Absolute data offset (for files) or node index (for directories)"""

    data_size: int
    """Size of the file data in bytes"""

    padding: int
    """Unknown/padding bytes"""

    name: str
    """Resolved string name of the entry"""

    data: bytes
    """Raw binary data of the file (empty for directories)"""

    def __init__(self):
        self.file_id: int = 0
        self.name_hash: int = 0
        self.attributes: int = 0
        self.type: int = 0
        self.name_offset: int = 0
        self.data_offset_or_idx: int = 0
        self.data_size: int = 0
        self.padding: int = 0
        self.name: str = ""
        self.data: bytes = b""


class Rarc:
    """
    Main class for reading, modifying, and writing RARC (Nintendo Archive) files

    See Also:
        - `YAGCD - RARC <https://hitmen.c02.at/files/yagcd/yagcd/chap15.html#sec15.3>`_
        - `Pikmin Technical Knowledge Base - RARC file <https://pikmintkb.com/wiki/RARC_file>`_
        - `Custom Mario Kart Wiiki - RARC (File Format) <https://wiki.tockdom.com/wiki/RARC_(File_Format)>`_
    """

    base_offset: int
    """Absolute stream offset where the RARC file begins"""

    magic_word: str
    """File signature, expected to be `RARC`"""

    file_length: int
    """Total length of the RARC file"""

    data_offset: int
    """Offset where the actual file data payload begins"""

    data_length: int
    """Total length of the data payload"""

    number_nodes: int
    """Total number of directory nodes in the archive"""

    offset_first_node: int
    """Offset to the first node definition"""

    total_directory: int
    """Total number of file and directory entries"""

    offset_first_directory: int
    """Offset to the first entry definition"""

    string_table_length: int
    """Size of the string table in bytes"""

    string_table_offset: int
    """Offset to the start of the string table"""

    number_of_files: int
    """Total number of actual files (excluding directories)"""

    nodes: List[RarcNode]
    """Collection of all directory nodes"""

    entries: List[RarcFileEntry]
    """Collection of all file and directory entries"""

    string_table: bytes
    """Raw bytes of the string table"""

    def __init__(self):
        # Header
        self.base_offset: int = 0
        self.magic_word: str = ""
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

    @classmethod
    def read(cls, stream: BinaryIO) -> "Rarc":
        """
        Reads and parses a RARC archive from a binary stream

        Args:
            stream: The binary stream containing the RARC data

        Returns:
            A populated Rarc instance

        Raises:
            ValueError: If the stream does not start with the correct RARC magic word

        Notes:
            Advances the stream position to the byte immediately after the RARC data
        """
        obj = cls()
        obj.base_offset = stream.tell()

        obj.magic_word = read_string(stream, 0x04)
        if obj.magic_word != "RARC":
            raise ValueError("Trying to read a non-rarc file with the rarc struct")

        obj.file_length = read_u32(stream)
        read_u32(stream)  # Length of header, always 0x20

        obj.data_offset = read_u32(stream)
        obj.data_length = read_u32(stream)
        stream.read(0xC)

        info_block_pos = stream.tell()

        obj.number_nodes = read_u32(stream)
        obj.offset_first_node = read_u32(stream)
        obj.total_directory = read_u32(stream)
        obj.offset_first_directory = read_u32(stream)
        obj.string_table_length = read_u32(stream)
        obj.string_table_offset = read_u32(stream)
        obj.number_of_files = read_u16(stream)

        read_u16(stream)
        read_u32(stream)

        # Read nodes
        stream.seek(info_block_pos + obj.offset_first_node)
        for _ in range(obj.number_nodes):
            node = RarcNode()
            node.type = read_string(stream, 4)
            node.name_offset = read_u32(stream)
            node.name_hash = read_u16(stream)
            node.entry_count = read_u16(stream)
            node.first_entry_index = read_u32(stream)
            obj.nodes.append(node)

        # Read file entries
        stream.seek(info_block_pos + obj.offset_first_directory)
        for _ in range(obj.total_directory):
            entry = RarcFileEntry()
            entry.file_id = read_u16(stream)
            entry.name_hash = read_u16(stream)
            entry.attributes = read_u32(stream)
            entry.type = entry.attributes >> 24
            entry.name_offset = entry.attributes & 0x00FFFFFF
            entry.data_offset_or_idx = read_u32(stream)
            entry.data_size = read_u32(stream)
            entry.padding = read_u32(stream)
            obj.entries.append(entry)

        # Read string table
        stream.seek(info_block_pos + obj.string_table_offset)
        obj.string_table = stream.read(obj.string_table_length)

        # Resolve names and read data
        for entry in obj.entries:
            end = obj.string_table.find(b'\x00', entry.name_offset)
            if end != -1:
                entry.name = obj.string_table[entry.name_offset:end].decode('utf-8', errors='ignore')
            else:
                entry.name = obj.string_table[entry.name_offset:].decode('utf-8', errors='ignore')

            if entry.file_id != 0xFFFF and entry.type != 0x02:
                abs_data_offset = obj.base_offset + 0x20 + obj.data_offset + entry.data_offset_or_idx
                current_pos = stream.tell()
                stream.seek(abs_data_offset)
                entry.data = stream.read(entry.data_size)
                stream.seek(current_pos)

        stream.seek(obj.base_offset + obj.file_length)
        return obj

    def extract_to(self, output_dir: str):
        """
        Extracts the entire RARC archive into a local directory structure

        Args:
            output_dir: The root directory where files will be extracted
        """
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

            if entry.file_id == 0xFFFF or entry.type == 0x02:
                # Subdirectory
                child_node = self.nodes[entry.data_offset_or_idx]
                self._extract_node(child_node, path)
            else:
                # File
                with open(path, "wb") as f:
                    f.write(entry.data)

    def write(self, stream: BinaryIO):
        """
        Packs the current RARC object structure back into a binary stream

        Args:
            stream: The binary stream to write the packed RARC data into
        """
        string_table_bytes = bytearray()
        string_map = {}

        def add_string(name: str) -> int:
            if name in string_map:
                return string_map[name]
            offset = len(string_table_bytes)
            string_map[name] = offset
            string_table_bytes.extend(name.encode('utf-8') + b'\x00')
            return offset

        def compute_hash(name: str) -> int:
            h = 0
            for c in name:
                h = (h * 3) + ord(c)
                h &= 0xFFFF
            return h

        # Pack nodes
        for node in self.nodes:
            node_name = node.type.strip('\x00')
            node.name_offset = add_string(node_name)
            node.name_hash = compute_hash(node_name)

        # Pack entries
        for entry in self.entries:
            entry.name_offset = add_string(entry.name)
            entry.name_hash = compute_hash(entry.name)

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
            if entry.file_id != 0xFFFF and entry.type != 0x02:
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
        stream.write(b"RARC")
        stream.write(self.file_length.to_bytes(4, 'big'))
        stream.write((0x20).to_bytes(4, 'big'))
        stream.write(self.data_offset.to_bytes(4, 'big'))
        stream.write(self.data_length.to_bytes(4, 'big'))
        stream.write(b'\x00' * 12)

        # Info block (at 0x20)
        stream.write(self.number_nodes.to_bytes(4, 'big'))
        stream.write(self.offset_first_node.to_bytes(4, 'big'))
        stream.write(self.total_directory.to_bytes(4, 'big'))
        stream.write(self.offset_first_directory.to_bytes(4, 'big'))
        stream.write(self.string_table_length.to_bytes(4, 'big'))
        stream.write(self.string_table_offset.to_bytes(4, 'big'))

        file_id_counter = 0
        for entry in self.entries:
            if entry.file_id != 0xFFFF:
                file_id_counter += 1

        stream.write(file_id_counter.to_bytes(2, 'big'))
        stream.write(b'\x00\x00')
        stream.write(b'\x00\x00\x00\x00')

        # Nodes
        for node in self.nodes:
            stream.write(node.type.ljust(4, '\x00').encode('ascii')[:4])
            stream.write(node.name_offset.to_bytes(4, 'big'))
            stream.write(node.name_hash.to_bytes(2, 'big'))
            stream.write(node.entry_count.to_bytes(2, 'big'))
            stream.write(node.first_entry_index.to_bytes(4, 'big'))

        # Entries
        for entry in self.entries:
            stream.write(entry.file_id.to_bytes(2, 'big'))
            stream.write(entry.name_hash.to_bytes(2, 'big'))
            attr = (entry.type << 24) | (entry.name_offset & 0x00FFFFFF)
            stream.write(attr.to_bytes(4, 'big'))
            stream.write(entry.data_offset_or_idx.to_bytes(4, 'big'))
            stream.write(entry.data_size.to_bytes(4, 'big'))
            stream.write((0).to_bytes(4, 'big'))

        # String table
        stream.write(self.string_table)

        # Data payload
        stream.write(payload)

    def get_file(self, name: str) -> bytes:
        """
        Retrieves file data by its exact name, regardless of path

        Args:
            name: The precise filename to look for

        Returns:
            The raw data of the file

        Raises:
            FileNotFoundError: If the file is not found in the entries
        """
        for entry in self.entries:
            if entry.name == name and entry.file_id != 0xFFFF and entry.type != 0x02:
                return entry.data

        raise FileNotFoundError(f"File not found in RARC: {name}")

    def replace_file(self, name: str, data: bytes) -> None:
        """Replaces the data of a file based on its exact name

        Args:
            name: The precise filename to modify
            data: The new binary data for the file

        Raises:
            FileNotFoundError: If the file is not found in the entries
        """
        for entry in self.entries:
            if entry.name == name and entry.file_id != 0xFFFF and entry.type != 0x02:
                entry.data = data
                return

        raise FileNotFoundError(f"File not found in RARC: {name}")