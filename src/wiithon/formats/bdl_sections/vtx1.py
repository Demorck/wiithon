"""
from enum import IntEnum
from typing import BinaryIO

from wiithon.binary.align import align
from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bdl_sections.bdl_section import BDLSection, PADDING_STRING

VTX1_MAGIC = "VTX1"
COLOR_DATA_COUNT = 2
TEX_DATA_COUNT = 8

class GXAttr(IntEnum):
    POSITION_MATRIX = 0x00
    TEX_MATRIX_0 = 0x01
    TEX_MATRIX_1 = 0x02
    TEX_MATRIX_2 = 0x03
    TEX_MATRIX_3 = 0x04
    TEX_MATRIX_4 = 0x05
    TEX_MATRIX_5 = 0x06
    TEX_MATRIX_6 = 0x07
    TEX_MATRIX_7 = 0x08
    POSITION = 0x09
    NORMAL = 0x0A
    COLOR_0 = 0x0B
    COLOR_1 = 0x0C
    TEX_0 = 0x0D
    TEX_1 = 0x0E
    TEX_2 = 0x0F
    TEX_3 = 0x10
    TEX_4 = 0x11
    TEX_5 = 0x12
    TEX_6 = 0x13
    TEX_7 = 0x14
    TANGENT = 0x19
    END = 0xFF

class GXCompTypePrimitve(IntEnum):
    U8 = 0x0
    S8 = 0x1
    U16 = 0x2
    S16 = 0x3
    FLOAT = 0x4

class GXCompTypeColor(IntEnum):
    RGB565 = 0x0
    RGB8 = 0x1
    RGBX8 = 0x2
    RGBA4 = 0x3
    RGBA6 = 0x4
    RGBA8 = 0x5

class VertexBuffer:
    def __init__(self) -> None:
        self.array_type: GXAttr = None
        self.component_count: int = 0
        self.component_type: GXCompTypePrimitve | GXCompTypeColor = None
        self.component_shift: int = 0

    @classmethod
    def read(cls, stream: BinaryIO) -> "VertexBuffer":
        obj = cls()
        reader = BinaryReader(stream)

        obj.array_type = GXAttr(reader.u32())
        obj.component_count = reader.u32()

        comp_type = reader.u32()
        if obj.array_type == GXAttr.COLOR_0 or obj.array_type == GXAttr.COLOR_1:
            obj.component_type = GXCompTypeColor(comp_type)
        else:
            obj.component_type = GXCompTypePrimitve(comp_type)

        obj.component_shift = reader.u8()
        
        reader.skip(3)

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.u32(self.array_type)
        writer.u32(self.component_count)
        writer.u32(self.component_type)
        writer.u8(self.component_shift)
        writer.pad(3, b'\xFF')

class Vertex:
    def __init__(self):
        self.buffer: VertexBuffer = None

        self.data: bytes = b''

    @staticmethod
    def get_buffer_component_size(buffer: VertexBuffer) -> int:
        if buffer.array_type == GXAttr.COLOR_0 or buffer.array_type == GXAttr.COLOR_1:
            match buffer.component_type:
                case GXCompTypeColor.RGB565 | GXCompTypeColor.RGBA4:
                    return 2
                case GXCompTypeColor.RGB8 | GXCompTypeColor.RGBX8:
                    return 3
                case GXCompTypeColor.RGBA6 | GXCompTypeColor.RGBA8:
                    return 4
                case _:
                    raise ValueError(f"Unknown GXCompType: {buffer.component_type}")
        else:
            match buffer.component_type:
                case GXCompTypePrimitve.U8 | GXCompTypePrimitve.S8:
                    return 1
                case GXCompTypePrimitve.U16 | GXCompTypePrimitve.S16:
                    return 2
                case GXCompTypePrimitve.FLOAT:
                    return 4
                case _:
                    raise ValueError(f"Unknown GXCompType: {buffer.component_type}")

    @staticmethod
    def get_buffer_component_count(buffer: VertexBuffer) -> int:
        match buffer.array_type:
            case GXAttr.POSITION:
                match buffer.component_count:
                    case 0:
                        return 2
                    case 1:
                        return 3
            case GXAttr.NORMAL:
                match buffer.component_count:
                    case 0:
                        return 3
                    case 1:
                        raise NotImplementedError("Unable to determine NORMAL_NBT component count.")
                    case 2:
                        raise NotImplementedError("Unable to determine NORMAL_NBT3 component count.")
            case GXAttr.COLOR_0 | GXAttr.COLOR_1:
                match buffer.component_count:
                    case 0:
                        return 3
                    case 1:
                        return 4
            case GXAttr.TEX_0 | GXAttr.TEX_1 | GXAttr.TEX_2 | GXAttr.TEX_3 | GXAttr.TEX_4 | GXAttr.TEX_5 | GXAttr.TEX_6 | GXAttr.TEX_7:
                match buffer.component_count:
                    case 0:
                        raise NotImplementedError("Unable to determine TEXCOORD_S component count.")
                    case 1:
                        return 2
            case GXAttr.END:
                return 0

    @classmethod
    def read(cls, stream: BinaryIO, buffer: VertexBuffer, vertex_count: int) -> "Vertex":
        obj = cls()
        reader = BinaryReader(stream)

        obj.buffer = buffer
        print(buffer.array_type, buffer.component_type, buffer.component_count)
        component_size = obj.get_buffer_component_size(buffer)
        component_count = obj.get_buffer_component_count(buffer)
        print(component_size, component_count)
        obj.data = reader.raw(vertex_count * component_size * component_count)

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.raw(self.data)

class VTX1Section(BDLSection):
    def __init__(self) -> None:
        self.magic = VTX1_MAGIC

        self.vertices: list[Vertex] = []

    @classmethod
    def read(cls, stream: BinaryIO, vertex_count: int) -> "VTX1Section":
        obj = cls()
        reader = BinaryReader(stream)

        section_start = reader.tell() - 8

        offsets = reader.list_u32(14)
        offsets = [offset for offset in offsets if offset != 0]

        reader.seek(section_start + offsets[0])

        buffers: list[VertexBuffer] = []

        while True:
            vertex = VertexBuffer.read(reader.stream)
            buffers.append(vertex)

            if vertex.array_type == GXAttr.END:
                break

        if len(offsets) != len(buffers):
            raise ValueError(f"Non-matching offsets and vertex buffers. Offsets: {len(offsets)}, buffers: {len(buffers)}.")
            
        for buffer, offset in zip(buffers, offsets):
            reader.seek(section_start + offset)

            vertex = Vertex.read(reader.stream, buffer, vertex_count)
            obj.vertices.append(vertex)

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        section_start = writer.tell() - 8

        writer.list_u32([0] * 14)

        buffers = [vertex.buffer for vertex in self.vertices]

        vertex_buffer_offset = writer.tell()

        writer.seek(section_start + 0x8)
        writer.u32(vertex_buffer_offset)
        writer.seek(vertex_buffer_offset)

        write_offsets: list[int] = []
        for buffer in buffers:
            match buffer.array_type:
                case GXAttr.POSITION:
                    offset = 0xC
                case GXAttr.NORMAL:
                    offset = 0x10
                case GXAttr.TANGENT:
                    offset = 0x14
                case GXAttr.COLOR_0:
                    offset = 0x18
                case GXAttr.COLOR_1:
                    offset = 0x1C
                case GXAttr.TEX_0:
                    offset = 0x20
                case GXAttr.TEX_1:
                    offset = 0x24
                case GXAttr.TEX_2:
                    offset = 0x28
                case GXAttr.TEX_3:
                    offset = 0x2C
                case GXAttr.TEX_4:
                    offset = 0x30
                case GXAttr.TEX_5:
                    offset = 0x34
                case GXAttr.TEX_6:
                    offset = 0x38
                case GXAttr.TEX_7:
                    offset = 0x3C
            
            buffer.write(writer.stream)
            write_offsets.append(offset)

        pad_boundary = align(writer.tell(), 0x20)
        pad_size = pad_boundary - writer.tell()
        writer.string(PADDING_STRING[:pad_size])
        print(hex(pad_boundary), hex(writer.tell()))

        for vertex, write_offset in zip(self.vertices, write_offsets):
            vertex_offset = writer.tell()

            writer.seek(section_start + write_offset)
            writer.u32(vertex_offset)
            writer.seek(vertex_offset)

            vertex.write(writer.stream)

            pad_boundary = align(writer.tell(), 0x20)
            pad_size = pad_boundary - writer.tell()
            writer.string(PADDING_STRING[:pad_size])
"""
