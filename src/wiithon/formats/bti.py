from enum import Enum, IntEnum
from typing import BinaryIO, NamedTuple

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter

class GXTexFormat(IntEnum):
    I4 = 0x0
    I8 = 0x1
    IA4 = 0x2
    IA8 = 0x3
    RGB565 = 0x4
    RGB5A3 = 0x5
    RGBA32 = 0x6
    C4 = 0x8
    C8 = 0x9
    C14X2 = 0xA
    CMPR = 0xE

class FormatNames(NamedTuple):
    bits_per_pixel: int
    block_width: int
    block_height: int

format: dict[GXTexFormat, FormatNames] = {
    GXTexFormat.I4: FormatNames(4, 8, 8),
    GXTexFormat.I8: FormatNames(8, 8, 4),
    GXTexFormat.IA4: FormatNames(8, 8, 4),
    GXTexFormat.IA8: FormatNames(16, 4, 4),
    GXTexFormat.RGB565: FormatNames(16, 4, 4),
    GXTexFormat.RGB5A3: FormatNames(16, 4, 4),
    GXTexFormat.RGBA32: FormatNames(32, 4, 4),
    GXTexFormat.C4: FormatNames(4, 8, 8),
    GXTexFormat.C8: FormatNames(8, 8, 4),
    GXTexFormat.C14X2: FormatNames(16, 4, 4),
    GXTexFormat.CMPR: FormatNames(4, 8, 8)
}

class BTIHeader:
    def __init__(self):
        self.format: GXTexFormat = 0
        self.alpha_enabled: bool = False
        self.width: int = 0
        self.height: int = 0
        self.wrap_s: int = 0
        self.wrap_t: int = 0
        self.palette_enabled: bool = False
        self.palette_format: int = 0
        self.palette_count: int = 0
        self.palette_offset: int = 0
        self.mipmap_enabled: bool = False
        self.is_edge_lod: bool = False
        self.bias_clamp: bool = False
        self.max_anisotropy: int = 0
        self.min_filter: int = 0
        self.max_filter: int = 0
        self.min_lod: int = 0
        self.max_lod: int = 0
        self.mipmap_count: int = 0
        self.lod_bias: int = 0
        self.texture_offset: int = 0

    @classmethod
    def read(cls, stream: BinaryIO) -> "BTIHeader":
        obj = cls()
        reader = BinaryReader(stream)

        obj.format = reader.u8()
        obj.alpha_enabled = reader.u8()
        obj.width = reader.u16()
        obj.height = reader.u16()
        obj.wrap_s = reader.u8()
        obj.wrap_t = reader.u8()
        obj.palette_enabled = reader.u8()
        obj.palette_format = reader.u8()
        obj.palette_count = reader.u16()
        obj.palette_offset = reader.u32()
        obj.mipmap_enabled = reader.u8()
        obj.is_edge_lod = reader.u8()
        obj.bias_clamp = reader.u8()
        obj.max_anisotropy = reader.u8()
        obj.min_filter = reader.u8()
        obj.max_filter = reader.u8()
        obj.min_lod = reader.u8()
        obj.max_lod = reader.u8()
        obj.mipmap_count = reader.u8()
        reader.skip(1)
        obj.lod_bias = reader.u16()
        obj.texture_offset = reader.u32()

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.u8(self.format)
        writer.u8(self.alpha_enabled)
        writer.u16(self.width)
        writer.u16(self.height)
        writer.u8(self.wrap_s)
        writer.u8(self.wrap_t)
        writer.u8(self.palette_enabled)
        writer.u8(self.palette_format)
        writer.u16(self.palette_count)
        writer.u32(self.palette_offset)
        writer.u8(self.mipmap_enabled)
        writer.u8(self.is_edge_lod)
        writer.u8(self.bias_clamp)
        writer.u8(self.max_anisotropy)
        writer.u8(self.min_filter)
        writer.u8(self.max_filter)
        writer.u8(self.min_lod)
        writer.u8(self.max_lod)
        writer.u8(self.mipmap_count)
        writer.pad(1)
        writer.u16(self.lod_bias)
        writer.u32(self.texture_offset)

class BTI:
    def __init__(self):
        self.name: str = ''
        
        self.header: BTIHeader = None
        self.palette_data: bytes = b''
        self.texture_data: bytes = b''

    @classmethod
    def read(cls, stream: BinaryIO) -> "BTI":
        obj = cls()
        reader = BinaryReader(stream)

        file_start = reader.tell()

        obj.header = BTIHeader.read(reader.stream)

        if obj.header.palette_enabled:
            pass

        reader.seek(file_start + obj.header.texture_offset)

        bits, width, height = format[obj.header.format]
        texture_size = int(obj.header.width * obj.header.height * bits / 8)
        obj.texture_data = reader.raw(texture_size)

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        file_start = writer.tell()

        self.header.write(writer.stream)

        if self.header.palette_enabled:
            writer.seek(file_start + self.header.palette_offset)
            writer.raw(self.palette_data)

        writer.seek(file_start + self.header.texture_offset)
        print(hex(writer.tell()))
        writer.raw(self.texture_data)
