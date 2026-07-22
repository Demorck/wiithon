from enum import IntEnum
from io import BytesIO
import wiithon.helpers.Utils as fh
from wiithon.file_helper.bmg_sections.bmg_section import BMGSection

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
    def import_node(cls, raw_bytes: BytesIO) -> "FLWTextNode":
        assert raw_bytes.seek(0, 2) == NODE_SIZE

        unknown1 = fh.read_u8(raw_bytes, 0x1)
        message_ID = fh.read_u16(raw_bytes, 0x2)
        next_flow_ID = fh.read_u16(raw_bytes, 0x4)
        validity = fh.read_u8(raw_bytes, 0x6)
        unknown2 = fh.read_u8(raw_bytes, 0x7)

        return cls(unknown1, message_ID, next_flow_ID, validity, unknown2)
    
    def export_node(self) -> BytesIO:
        data = BytesIO()

        fh.write_u8(data, self.node_type, 0x0)
        fh.write_u8(data, self.unknown1, 0x1)
        fh.write_u16(data, self.message_ID, 0x2)
        fh.write_u16(data, self.next_flow_ID, 0x4)
        fh.write_u8(data, self.validity, 0x6)
        fh.write_u8(data, self.unknown2, 0x7)

        return data

class FLWConditionNode:
    node_type: int = 2

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
    def import_node(cls, raw_bytes: BytesIO) -> "FLWConditionNode":
        assert raw_bytes.seek(0, 2) == NODE_SIZE

        unknown1 = fh.read_u8(raw_bytes, 0x1)
        condition_type = fh.read_u16(raw_bytes, 0x2)
        condition_argument = fh.read_u16(raw_bytes, 0x4)
        branch_node_ID = fh.read_u16(raw_bytes, 0x6)

        return cls(unknown1, condition_type, condition_argument, branch_node_ID)
    
    def export_node(self) -> BytesIO:
        data = BytesIO()

        fh.write_u8(data, self.node_type, 0x0)
        fh.write_u8(data, self.unknown1, 0x1)
        fh.write_u16(data, self.condition_type, 0x2)
        fh.write_u16(data, self.condition_argument, 0x4)
        fh.write_u16(data, self.branch_node_ID, 0x6)

        return data

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
    def import_node(cls, raw_bytes: BytesIO) -> "FLWEventNode":
        assert raw_bytes.seek(0, 2) == NODE_SIZE

        event_type = fh.read_u8(raw_bytes, 0x1)
        branch_node_ID = fh.read_u16(raw_bytes, 0x2)
        event_argument = fh.read_u32(raw_bytes, 0x4)

        return cls(event_type, branch_node_ID, event_argument)
    
    def export_node(self) -> BytesIO:
        data = BytesIO()

        fh.write_u8(data, self.node_type, 0x0)
        fh.write_u8(data, self.event_type, 0x1)
        fh.write_u16(data, self.branch_node_ID, 0x2)
        fh.write_u32(data, self.event_argument, 0x4)

        return data

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
    def import_section(cls, raw_bytes: BytesIO) -> "FLW1Section":
        section = cls()
        
        flow_node_count = fh.read_u16(raw_bytes, 0x0)
        branch_node_count = fh.read_u16(raw_bytes, 0x2)
        
        offset = 0x8
        for flow_node_index in range(flow_node_count):
            node_type = fh.read_u8(raw_bytes, offset)
            node_bytes = fh.read_bytes(raw_bytes, 0x8, offset)
            node_bytes = BytesIO(node_bytes)

            if node_type == NodeType.text:
                node = FLWTextNode.import_node(node_bytes)
            elif node_type == NodeType.condition:
                node = FLWConditionNode.import_node(node_bytes)
            elif node_type == NodeType.event:
                node = FLWEventNode.import_node(node_bytes)
            
            section.flow_nodes.append(node)
            offset += 0x8
        
        for _ in range(branch_node_count):
            branch_node_id = fh.read_u16(raw_bytes, offset)
            section.branch_nodes.append(branch_node_id)
            offset += 0x2
        
        return section
    
    def export_section(self) -> BytesIO:
        data = BytesIO()

        self.flow_node_count = len(self.flow_nodes)
        self.branch_node_count = len(self.branch_nodes)

        fh.write_u16(data, self.flow_node_count, 0x0)
        fh.write_u16(data, self.branch_node_count, 0x2)
        fh.write_u32(data, 0, 0x4)

        offset = 0x8
        for flow_node in self.flow_nodes:
            flow_data = flow_node.export_node()
            fh.write_bytes(data, flow_data.getvalue(), offset)

            offset += 0x8

        for branch_node in self.branch_nodes:
            fh.write_u16(data, branch_node, offset)
            
            offset += 0x2
        
        return data
