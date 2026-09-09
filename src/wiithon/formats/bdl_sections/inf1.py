from enum import IntEnum
from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bdl_sections.bdl_section import BDLSection

INF1_MAGIC = "INF1"

class HierarchyNodeType(IntEnum):
    finish = 0x00
    new = 0x01
    end = 0x02
    joint = 0x10
    material = 0x11
    shape = 0x12

class HierarchyNode:
    def __init__(self) -> None:
        self.node_type: HierarchyNodeType = None
        self.data: int = 0

    @classmethod
    def read(cls, stream: BinaryIO) -> "HierarchyNode":
        obj = cls()
        reader = BinaryReader(stream)

        obj.node_type = HierarchyNodeType(reader.u16())
        obj.data = reader.u16()
        
        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.u16(self.node_type)
        writer.u16(self.data)

class INF1Section(BDLSection):
    def __init__(self) -> None:
        self.magic = INF1_MAGIC

        self.flags: int = 0
        self.matrix_group_count: int = 0
        self.vertex_count: int = 0

        self.hierarchy_nodes: list[HierarchyNode] = []

    @classmethod
    def read(cls, stream: BinaryIO) -> "INF1Section":
        obj = cls()
        reader = BinaryReader(stream)

        section_start = reader.tell() - 8

        obj.flags = reader.u16()
        reader.skip(0x2)
        obj.matrix_group_count = reader.u32()
        obj.vertex_count = reader.u32()

        hierarchy_data_offset = reader.u32()

        reader.seek(section_start + hierarchy_data_offset)

        while True:
            hierarchy_node = HierarchyNode.read(reader.stream)
            obj.hierarchy_nodes.append(hierarchy_node)

            if hierarchy_node.node_type == HierarchyNodeType.finish:
                break

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        section_start = writer.tell() - 8
        
        writer.u16(self.flags)
        writer.pad(0x2, b'\xFF')
        writer.u32(self.matrix_group_count)
        writer.u32(self.vertex_count)
        writer.u32(writer.tell() + 4 - section_start)

        for hierarchy_node in self.hierarchy_nodes:
            hierarchy_node.write(writer.stream)
