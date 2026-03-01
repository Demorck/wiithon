from typing import List, BinaryIO

from helpers.Utils import read_shiftjis
from file_system_table.FSTNode import FSTNode, FSTDirectory, FSTFile
from file_system_table.RawNode import RawFSTNode


class FST:
    def __init__(self):
        self.entries: List[FSTNode] = []

    @classmethod
    def read(cls, stream: BinaryIO, offset: int) -> "FST":
        obj = cls()

        stream.seek(offset)
        root = RawFSTNode.read(stream)
        total_nodes = root.length
        nodes: List[RawFSTNode] = [root]
        for _ in range(total_nodes - 1):
            nodes.append(RawFSTNode.read(stream))

        string_offset = stream.tell()
        obj.entries, _ = _build_tree(stream, string_offset, nodes,
                                     start=1, end=total_nodes)

        return obj

    def write(self, stream: BinaryIO) -> None:
        """Write this FST to a binary stream.
        Converts the tree back to flat raw nodes + string table.
        :param stream: Binary stream to write to.
        """
        raw_nodes: list[RawFSTNode] = []
        strings: bytearray = bytearray()

        root = RawFSTNode()
        root.is_dir = True
        root.name_offset = 0
        root.data_offset = 0
        raw_nodes.append(root)

        _flatten_tree(self.entries, raw_nodes, strings)

        raw_nodes[0].length = len(raw_nodes)

        for node in raw_nodes:
            node.write(stream)

        stream.write(strings)

    def count_files(self) -> int:
        return sum(e.count_files() for e in self.entries)



def _build_tree(stream: BinaryIO, string_offset: int,
                nodes: List[RawFSTNode],
                start: int, end: int) -> tuple[List[FSTNode], int]:
    """Recursively convert flat raw nodes into a tree.

    :param stream: Binary stream (for reading names from string table).
    :param string_offset: Offset of the string table in the stream.
    :param nodes: Flat list of all raw nodes.
    :param start: First index to process.
    :param end: Stop before this index.

    :return: list of FSTNodes, next index to process.
    """
    result: List[FSTNode] = []
    i = start

    while i < end:
        raw = nodes[i]
        name = read_shiftjis(stream, string_offset + raw.name_offset)

        if raw.is_directory:
            children, _ = _build_tree(stream, string_offset, nodes,
                                      start=i + 1, end=raw.length)
            directory = FSTDirectory(name)
            directory.children = children
            result.append(directory)
            i = raw.length
        else:
            result.append(FSTFile(name, offset=raw.data_offset, length=raw.length))
            i += 1

    return result, i


def _add_string(strings: bytearray, name: str) -> int:
    """
    Add a Shift-JIS encoded name to the string table
    :param strings: The string table being built
    :param name: The filename to add
    :return: Offset of the name within the string table.
    """
    offset = len(strings)
    encoded = name.encode('shift_jis')
    strings.extend(encoded)
    strings.append(0) # Null terminator
    return offset

def _flatten_tree(entries: list[FSTNode], raw_nodes: list[RawFSTNode],
                  strings: bytearray, parent_index: int = 0) -> None:
    """
    Recursively flatten the tree into raw nodes and string table

    :param entries: List of FSTNode children to process
    :param raw_nodes: Flat list being built (mutated in place)
    :param strings: String table being built (mutated in place)
    """
    for entry in entries:
        raw = RawFSTNode()
        raw.name_offset = _add_string(strings, entry.name)
        if isinstance(entry, FSTDirectory):
            raw.is_directory = True
            raw.data_offset = parent_index
            raw_nodes.append(raw)
            current_index = len(raw_nodes) - 1
            _flatten_tree(entry.children, raw_nodes, strings, current_index)
            raw.length = len(raw_nodes)

        elif isinstance(entry, FSTFile):
            raw.is_directory = False
            raw.data_offset = entry.offset
            raw.length = entry.length
            raw_nodes.append(raw)

        else:
            raise NotImplementedError