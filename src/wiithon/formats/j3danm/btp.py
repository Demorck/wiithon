from io import BytesIO
from typing import BinaryIO, ClassVar

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.exceptions import InvalidFormatError
from wiithon.formats.j3danm.j3d import PAD_BYTE, J3DAnmBase, LoopMode


class BTPKeyFrame:
    def __init__(self, material_name: str, material_name_index: int, texture_indices: list[int], material_index: int):
        self.material_name: str = material_name # Material name in the name table
        self.material_name_index: int = material_name_index # Material index into the name table
        self.texture_indices: list[int] = texture_indices
        self.material_index: int = material_index # Material index in the model's materials


class BTP(J3DAnmBase):
    file_magic: ClassVar[str] = "btp1"
    section_magic: ClassVar[str] = "TPT1"
    section_count: ClassVar[int] = 1


    def __init__(self) -> None:
        self.duration: int = 0
        self.loop_mode: LoopMode = None
        self.keyframes: list[BTPKeyFrame] = []


    @classmethod
    def read(cls, stream: BinaryIO) -> "BTP":
        obj = cls()
        reader = BinaryReader(stream)

        _, section_count = obj.read_header(reader.stream)

        section_start = reader.tell()

        if section_count != obj.section_count:
            raise InvalidFormatError(f"Unexpected section count. Expected {obj.section_count}, got {section_count}.")

        # TPT section
        section_magic = reader.string(4)
        if section_magic != obj.section_magic:
            raise InvalidFormatError(f"Invalid file magic, {section_magic!r} instead of {obj.section_magic!r}")

        section_size = reader.u32()
        obj.loop_mode = LoopMode(reader.u8())
        reader.skip(1)
        obj.duration = reader.u16()
        keyframe_count = reader.u16()
        texture_index_count = reader.u16()

        # Offsets
        keyframe_offset = reader.u32()
        texture_index_offset = reader.u32()
        remap_table_offset = reader.u32()
        name_table_offset = reader.u32()

        # Keyframes
        reader.seek(section_start + name_table_offset)
        material_names = obj.read_name_table(reader.stream)

        for keyframe_index in range(keyframe_count):
            reader.seek(section_start + keyframe_offset + keyframe_index * 4)
            texture_count = reader.u16()
            first_index = reader.u16()
            material_name_index = reader.u8()

            reader.seek(section_start + texture_index_offset + first_index * 2)
            texture_indices: list[int] = []
            for texture_index in range(texture_count):
                texture_indices.append(reader.u16())

            reader.seek(section_start + remap_table_offset)
            remap_index = reader.u16()

            keyframe = BTPKeyFrame(material_names[keyframe_index], material_name_index, texture_indices, remap_index)
            obj.keyframes.append(keyframe)

        reader.seek(section_start + section_size)

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        file_start = writer.tell()

        self.write_header(writer.stream)

        section_start = writer.tell()

        # TPT1 section
        writer.string(self.section_magic)
        writer.u32(0) # Write the section size later
        writer.u8(self.loop_mode)
        writer.pad(1, PAD_BYTE)
        writer.u16(self.duration)
        writer.u16(len(self.keyframes))
        writer.u16(sum([len(keyframe.texture_indices) for keyframe in self.keyframes]))

        # Offsets
        writer.u32(0)
        writer.u32(0)
        writer.u32(0)
        writer.u32(0)

        # Keyframes
        keyframe_offset = writer.tell() - section_start

        first_index = 0
        for keyframe in self.keyframes:
            writer.u16(len(keyframe.texture_indices))
            writer.u16(first_index)
            writer.u8(keyframe.material_name_index)
            writer.pad(3, PAD_BYTE)

            first_index += len(keyframe.texture_indices)

        # Texture indices
        texture_index_offset = writer.tell() - section_start
        for keyframe in self.keyframes:
            for index in keyframe.texture_indices:
                writer.u16(index)

        self.pad_string(writer.stream, 0x4)

        # Remap table
        remap_table_offset = writer.tell() - section_start
        for keyframe in self.keyframes:
            writer.u16(keyframe.material_index)

        self.pad_string(writer.stream, 0x4)

        # Name table
        name_table_offset = writer.tell() - section_start

        # Write the offsets
        writer.seek(section_start + 0x10)
        writer.u32(keyframe_offset)
        writer.u32(texture_index_offset)
        writer.u32(remap_table_offset)
        writer.u32(name_table_offset)

        writer.seek(section_start + name_table_offset)
        self.write_name_table(writer.stream, [keyframe.material_name for keyframe in self.keyframes])

        # Section size
        section_size = writer.tell() - section_start
        writer.seek(section_start + 0x4)
        writer.u32(section_size)

        # File size
        writer.seek(file_start + 0x8)
        writer.u32(section_start + section_size - file_start)

        writer.seek(section_start + section_size)
