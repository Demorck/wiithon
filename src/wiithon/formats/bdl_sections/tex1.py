from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bdl_sections.bdl_section import BDLSection
from wiithon.formats.bti import BTI

TEX1_MAGIC = "TEX1"

class TEX1Section(BDLSection):
    def __init__(self) -> None:
        self.magic = TEX1_MAGIC

        self.textures: list[BTI] = []

    @classmethod
    def read(cls, stream: BinaryIO) -> "TEX1Section":
        obj = cls()
        reader = BinaryReader(stream)

        section_start = reader.tell() - 8

        texture_count = reader.u16()
        reader.skip(2)
        texture_header_offset = reader.u32()
        name_table_offset = reader.u32()

        for texture_index in range(texture_count):
            reader.seek(section_start + texture_header_offset + texture_index * 0x20)
            texture = BTI.read(reader.stream)
            obj.textures.append(texture)

        reader.seek(section_start + name_table_offset)
        texture_names = obj.read_string_table(reader.stream)

        for name, texture in zip(texture_names, obj.textures):
            texture.name = name

        return obj

    def calculate_header_offsets(self) -> None:
        total_offset = 0

        # Palette offset
        for i, texture in enumerate(self.textures):
            local_offset = (len(self.textures) - i) * 0x20

            texture.header.palette_offset = total_offset + local_offset
            if texture.header.palette_enabled:
                total_offset += len(texture.palette_data)

        # Texture offset
        for i, texture in enumerate(self.textures):
            local_offset = (len(self.textures) - i) * 0x20

            print(hex(total_offset + local_offset))
            texture.header.texture_offset = total_offset + local_offset
            total_offset += len(texture.texture_data)
        
    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        section_start = writer.tell() - 8

        writer.u16(len(self.textures))
        writer.pad(2, b'\xFF')
        writer.u32(0) # Write the offset to the textures later
        writer.u32(0) # Write the offset to the string table later

        self.write_padding(writer.stream, 0x20)

        texture_offset = writer.tell()

        writer.seek(section_start + 0xC)
        writer.u32(texture_offset - section_start)

        max_position = 0

        self.calculate_header_offsets()
        for i, texture in enumerate(self.textures):
            writer.seek(texture_offset + i * 0x20)
            texture.write(writer.stream)

            position = writer.tell()
            if position > max_position:
                max_position = position

        writer.seek(max_position)
        self.write_padding(writer.stream, 0x20)

        string_table_offset = writer.tell() - section_start
        writer.seek(section_start + 0x10)
        writer.u32(string_table_offset)
        writer.seek(section_start + string_table_offset)

        texture_names = [texture.name for texture in self.textures]
        self.write_string_table(writer.stream, texture_names)
