from enum import IntEnum
from typing import BinaryIO

from wiithon.binary.align import align
from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bmg_sections.bmg_section import BMGSection

FLW1_MAGIC: str = "FLW1"
type FLWNode = FLWTextNode | FLWConditionNode | FLWEventNode

class NodeType(IntEnum):
    text = 1
    condition = 2
    event = 3

class FLWTextNode:
    def __init__(self) -> None:
        self.node_type: NodeType = NodeType.text
        self.unknown1: int = 0
        self.message_id: int = 0
        self.next_flow_id: int = 0
        self.validity: int = 0
        self.unknown2: int = 0
    
    @classmethod
    def read(cls, stream: BinaryIO) -> "FLWTextNode":
        obj = cls()
        reader = BinaryReader(stream)

        obj.unknown1 = reader.u8()
        obj.message_id = reader.u16()
        obj.next_flow_id = reader.u16()
        obj.validity = reader.u8()
        obj.unknown2 = reader.u8()

        return obj
    
    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.u8(self.node_type)
        writer.u8(self.unknown1)
        writer.u16(self.message_id)
        writer.u16(self.next_flow_id)
        writer.u8(self.validity)
        writer.u8(self.unknown2)

class FLWConditionNode:
    def __init__(self) -> None:
        self.node_type: NodeType = NodeType.condition
        self.unknown1: int = 0
        self.condition_type: int = 0
        self.condition_argument: int = 0
        self.branch_node_id: int = 0
    
    @classmethod
    def read(cls, stream: BinaryIO) -> "FLWConditionNode":
        obj = cls()
        reader = BinaryReader(stream)

        obj.unknown1 = reader.u8()
        obj.condition_type = reader.u16()
        obj.condition_argument = reader.u16()
        obj.branch_node_id = reader.u16()

        return obj
    
    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.u8(self.node_type)
        writer.u8(self.unknown1)
        writer.u16(self.condition_type)
        writer.u16(self.condition_argument)
        writer.u16(self.branch_node_id)

class FLWEventNode:
    def __init__(self) -> None:
        self.node_type: NodeType = NodeType.event
        self.event_type: int = 0
        self.branch_node_id: int = 0
        self.event_argument: int = 0
    
    @classmethod
    def read(cls, stream: BinaryIO) -> "FLWEventNode":
        obj = cls()
        reader = BinaryReader(stream)

        obj.event_type = reader.u8()
        obj.branch_node_id = reader.u16()
        obj.event_argument = reader.u32()

        return obj
    
    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.u8(self.node_type)
        writer.u8(self.event_type)
        writer.u16(self.branch_node_id)
        writer.u32(self.event_argument)

class FLW1Section(BMGSection):
    def __init__(self) -> None:
        self.magic = FLW1_MAGIC
        
        self.flow_nodes: list[FLWNode] = []
        self.branch_nodes: list[int] = []
        self.unknown_list: list[int] = []

    @classmethod
    def read(cls, stream: BinaryIO) -> "FLW1Section":
        obj = cls()
        reader = BinaryReader(stream)

        flow_node_count = reader.u16()
        branch_node_count = reader.u16()
        reader.skip(4)

        for flow_node_index in range(flow_node_count):
            node_type = reader.u8()

            match node_type:
                case NodeType.text:
                    node = FLWTextNode.read(reader.stream)
                case NodeType.condition:
                    node = FLWConditionNode.read(reader.stream)
                case NodeType.event:
                    node = FLWEventNode.read(reader.stream)
            
            obj.flow_nodes.append(node)
        
        for branch_node_index in range(branch_node_count):
            branch_node_id = reader.u16()
            obj.branch_nodes.append(branch_node_id)

        # Hidden data?
        for branch_node_index in range(branch_node_count):
            unknown = reader.u8()
            obj.unknown_list.append(unknown)
        
        return obj
    
    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.u16(len(self.flow_nodes))
        writer.u16(len(self.branch_nodes))
        writer.pad(4)

        for flow_node in self.flow_nodes:
            flow_node.write(stream)

        for branch_node in self.branch_nodes:
            writer.u16(branch_node)

        for unknown in self.unknown_list:
            writer.u8(unknown)
