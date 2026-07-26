import os
import struct
from io import BytesIO
from typing import BinaryIO, List

from wiithon.crypto.layout import U8_MAGIC_WORD
from wiithon.binary.reader import read_u32
from wiithon.binary.align import align

NODE_SIZE = 0xC
ROOTNODE_OFFSET = 0x20

class U8Node:
    def __init__(self) -> None:
        self.is_dir: bool = False
        self.name_offset: int = 0
        self.data_offset: int = 0
        self.size: int = 0
        self.name: str = ""
        self.data: bytes = b""


class U8:
    def __init__(self) -> None:
        self.nodes : List[U8Node] = []


    @classmethod
    def read(cls, stream: BinaryIO) -> "U8":
        obj = cls()
        base = stream.tell()

        magic = stream.read(4)
        if magic != U8_MAGIC_WORD:
            raise ValueError(f"Invalid magic word for U8 {magic:!r} instead of {U8_MAGIC_WORD}")

        rootnode_offset = read_u32(stream) # Always 0x20
        header_size = read_u32(stream)

        read_u32(stream) # data offset, recomputed on write
        stream.read(0x10)

        stream.seek(base + rootnode_offset)

        raw_root_node = stream.read(NODE_SIZE)
        total_nodes = struct.unpack_from(">I", raw_root_node, 8)[0]
        raw_nodes = [raw_root_node]

        for _ in range(total_nodes - 1):
            raw_nodes.append(stream.read(NODE_SIZE))

        string_table = stream.read(header_size - total_nodes * NODE_SIZE)

        def _find_in_table(offset: int) -> str:
            end = string_table.find(b"\x00", offset)
            raw_string = string_table[offset:] if end == -1 else string_table[offset:end]
            return raw_string.decode('ascii', errors='replace')


        for raw_node in raw_nodes:
            node = U8Node()
            node.is_dir = raw_node[0] == 0x01
            node.name_offset = (raw_node[1] << 16) | (raw_node[2] << 8) | raw_node[3]
            node.data_offset = struct.unpack_from(">I", raw_node, 4)[0]
            node.size = struct.unpack_from(">I", raw_node, 8)[0]
            node.name = _find_in_table(node.name_offset)
            obj.nodes.append(node)


        for node in obj.nodes:
            if not node.is_dir:
                stream.seek(base + node.data_offset)
                node.data = stream.read(node.size)

        return obj

    def _search(self, parts: List[str], start: int, end: int) -> int | None:
        if not parts:
            return None

        i = start
        while i < end:
            node = self.nodes[i]
            if node.name == parts[0]:
                if len(parts) == 1:
                    return i
                if node.is_dir:
                    return self._search(parts[1:], i + 1, node.size)
                return None

            i = node.size if node.is_dir else i + 1

        return None

    def _node_index(self, path: str) -> int:
        parts = [p for p in path.split('/') if p]
        if not self.nodes:
            raise FileNotFoundError("Empty U8 archive")

        index = self._search(parts, 1, self.nodes[0].size)
        if index is None:
            raise FileNotFoundError(f"Not found in U8: {path}")

        return index

    def get_file(self, path: str) -> bytes:
        node = self.nodes[self._node_index(path)]
        if node.is_dir:
            raise FileNotFoundError(f"Path is directory: {path}")

        return node.data

    def replace_file(self, path: str, data: bytes) -> None:
        node = self.nodes[self._node_index(path)]
        if node.is_dir:
            raise FileNotFoundError(f"Path is directory: {path}")

        node.data = data
        node.size = len(data)

    def write(self, stream: BinaryIO) -> None:
        string_table: bytearray = bytearray()
        string_map: dict[str, int] = {}

        def _add(name: str) -> int:
            if name not in string_map:
                string_map[name] = len(string_table)
                string_table.extend(name.encode('ascii') + b'\x00')
            return string_map[name]

        for node in self.nodes:
            node.name_offset = _add(node.name)

        total_nodes  = len(self.nodes)
        header_size  = total_nodes * NODE_SIZE + len(string_table)
        data_section = align(ROOTNODE_OFFSET + header_size, 0x40)

        cursor = data_section
        for node in self.nodes:
            if not node.is_dir:
                node.data_offset = cursor
                node.size = len(node.data)
                cursor = align(cursor + node.size, 0x20)

        # Header
        stream.write(U8_MAGIC_WORD)
        stream.write(struct.pack(">I", ROOTNODE_OFFSET))
        stream.write(struct.pack(">I", header_size))
        stream.write(struct.pack(">I", data_section))
        stream.write(b'\x00' * 16)

        # Nodes
        for node in self.nodes:
            type_node = ((0x01 if node.is_dir else 0x00) << 24) | (node.name_offset & 0xFFFFFF)
            stream.write(struct.pack(">I", type_node))
            stream.write(struct.pack(">I", node.data_offset))
            stream.write(struct.pack(">I", node.size))

        # String table
        stream.write(string_table)

        # Padding
        stream.write(b"\x00" * (data_section - ROOTNODE_OFFSET - header_size))

        # File data (0x20 aligned)
        written = data_section
        for node in self.nodes:
            if not node.is_dir:
                stream.write(node.data)
                next_aligned = align(written + len(node.data), 0x20)
                stream.write(b'\x00' * (next_aligned - written - len(node.data)))
                written = next_aligned

    def get_bytes(self) -> bytes:
        buffer = BytesIO()
        self.write(buffer)
        return buffer.getvalue()

    # maybe change this function to a proper api
    def extract_to(self, output_dir: str) -> None:
        if not self.nodes:
            return

        self._extract(1, self.nodes[0].size, output_dir)

    def _extract(self, start: int, end: int, current_dir: str) -> None:
        os.makedirs(current_dir, exist_ok=True)
        i = start
        while i < end:
            node = self.nodes[i]
            path = os.path.join(current_dir, node.name)
            if node.is_dir:
                node_size = node.size
                self._extract(i + 1, node_size, path)
                i = node_size
            else:
                with open(path, "wb") as f:
                    f.write(node.data)
                i += 1

    def get_file_by_path(self, path: str) -> bytes:
        return self.get_file(path)

    def replace_file_by_path(self, path: str, data: bytes) -> None:
        self.replace_file(path, data)