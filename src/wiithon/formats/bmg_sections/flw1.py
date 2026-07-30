from enum import IntEnum
from io import BytesIO
from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bmg_sections.bmg_section import BMGSection

NODE_SIZE: int = 0x8
FLW1_MAGIC: str = "FLW1"
type FLWNode = FLWTextNode | FLWConditionNode | FLWEventNode

class NodeType(IntEnum):
    text = 1
    condition = 2
    event = 3

class FLWTextNode:
    node_type: int = NodeType.text

    def __init__(self,
                 unknown1: int,
                 message_ID: int,
                 next_flow_ID: int,
                 validity: int,
                 unknown2: int):
        
        self.unknown1: int = unknown1
        self.message_ID: int = message_ID
        self.next_flow_ID: int = next_flow_ID
        self.validity: int = validity
        self.unknown2: int = unknown2
    
    @classmethod
    def import_node(cls, raw_bytes: BinaryIO) -> "FLWTextNode":
        reader = BinaryReader(raw_bytes)
        assert reader.size() == NODE_SIZE
        assert reader.u8() == NodeType.text

        reader.skip(0x1)
        unknown1 = reader.u8()
        message_ID = reader.u16()
        next_flow_ID = reader.u16()
        validity = reader.u8()
        unknown2 = reader.u8()

        return cls(unknown1, message_ID, next_flow_ID, validity, unknown2)
    
    def export_node(self) -> BinaryIO:
        node_bytes = BytesIO()
        writer = BinaryWriter(node_bytes)

        writer.u8(self.node_type)
        writer.u8(self.unknown1)
        writer.u16(self.message_ID)
        writer.u16(self.next_flow_ID)
        writer.u8(self.validity)
        writer.u8(self.unknown2)

        return node_bytes

class FLWConditionNode:
    node_type: int = NodeType.condition

    def __init__(self,
                 unknown1: int,
                 condition_type: int,
                 condition_argument: int,
                 branch_node_ID: int):
        
        self.unknown1: int = unknown1
        self.condition_type: int = condition_type
        self.condition_argument: int = condition_argument
        self.branch_node_ID: int = branch_node_ID
    
    @classmethod
    def import_node(cls, raw_bytes: BinaryIO) -> "FLWConditionNode":
        reader = BinaryReader(raw_bytes)
        assert reader.size() == NODE_SIZE
        assert reader.u8() == NodeType.condition

        unknown1 = reader.u8()
        condition_type = reader.u16()
        condition_argument = reader.u16()
        branch_node_ID = reader.u16()

        return cls(unknown1, condition_type, condition_argument, branch_node_ID)
    
    def export_node(self) -> BinaryIO:
        node_bytes = BytesIO()
        writer = BinaryWriter(node_bytes)

        writer.u8(self.node_type)
        writer.u8(self.unknown1)
        writer.u16(self.condition_type)
        writer.u16(self.condition_argument)
        writer.u16(self.branch_node_ID)

        return node_bytes

class FLWEventNode:
    node_type: int = NodeType.event

    def __init__(self,
                 event_type: int,
                 branch_node_ID: int,
                 event_argument: int):
        
        self.event_type: int = event_type
        self.branch_node_ID: int = branch_node_ID
        self.event_argument: int = event_argument
    
    @classmethod
    def import_node(cls, raw_bytes: BinaryIO) -> "FLWEventNode":
        reader = BinaryReader(raw_bytes)
        assert reader.size() == NODE_SIZE
        assert reader.u8() == NodeType.event

        event_type = reader.u8()
        branch_node_ID = reader.u16()
        event_argument = reader.u32()

        return cls(event_type, branch_node_ID, event_argument)
    
    def export_node(self) -> BinaryIO:
        node_bytes = BytesIO()
        writer = BinaryWriter(node_bytes)

        writer.u8(self.node_type)
        writer.u8(self.event_type)
        writer.u16(self.branch_node_ID)
        writer.u32(self.event_argument)

        return node_bytes

class FLW1Section(BMGSection):
    """
    Represents a FLW1 (Flow) section containing flow nodes and branch nodes.
    This class handles the parsing and serialization of flow control data used in
    Wii game files. It manages a collection of flow nodes (text, condition, event)
    and branch node references.
    Attributes:
        flow_nodes (list[FLWNode]): List of flow nodes in this section.
        branch_nodes (list[int]): List of branch node IDs.
    Methods:
        __init__(flow_nodes, branch_nodes): Initialize a FLW1Section with optional
            flow nodes and branch nodes.
        import_section(raw_bytes): Class method that deserializes a FLW1Section
            from raw binary data (BytesIO). Reads the flow node count and branch
            node count from the header, then parses each node based on its type
            (text, condition, or event). Returns a populated FLW1Section instance.
        export_section(): Serializes the FLW1Section back into binary format (BytesIO).
            Writes the header with node counts, then serializes each flow node and
            branch node sequentially. Returns the packed data as BytesIO.
    """
    flow_nodes: list[FLWNode]
    branch_nodes: list[int]

    def __init__(self, flow_nodes: list[FLWNode] = None, branch_nodes: list[int] = None):
        super().__init__(FLW1_MAGIC)
        
        if flow_nodes == None:
            flow_nodes = []
        if branch_nodes == None:
            branch_nodes = []
        
        self.flow_node_count = len(flow_nodes)
        self.branch_node_count = len(branch_nodes)

        self.flow_nodes = flow_nodes
        self.branch_nodes = branch_nodes

    @classmethod
    def import_section(cls, raw_bytes: BinaryIO) -> "FLW1Section":
        reader = BinaryReader(raw_bytes)
        section = cls()

        flow_node_count = reader.u16()
        branch_node_count = reader.u16()
        reader.seek(0x8)

        for flow_node_index in range(flow_node_count):
            node_type = reader.u8()
            reader.back(0x1)
            node_bytes = reader.raw(NODE_SIZE)
            node_bytes = BytesIO(node_bytes)

            match node_type:
                case NodeType.text:
                    node = FLWTextNode.import_node(node_bytes)
                case NodeType.condition:
                    node = FLWConditionNode.import_node(node_bytes)
                case NodeType.event:
                    node = FLWEventNode.import_node(node_bytes)
            
            section.flow_nodes.append(node)
        
        for branch_node_index in range(branch_node_count):
            branch_node_id = reader.u16()
            section.branch_nodes.append(branch_node_id)
        
        return section
    
    def export_section(self) -> BinaryIO:
        section_bytes = BytesIO()
        writer = BinaryWriter(section_bytes)

        self.flow_node_count = len(self.flow_nodes)
        self.branch_node_count = len(self.branch_nodes)

        writer.u16(self.flow_node_count)
        writer.u16(self.branch_node_count)
        writer.seek(0x8)

        for flow_node in self.flow_nodes:
            flow_data = flow_node.export_node()
            writer.raw(flow_data.read)

        for branch_node in self.branch_nodes:
            writer.u16(branch_node)
        
        return section_bytes
