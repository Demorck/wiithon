from io import BytesIO
from typing import BinaryIO, ClassVar

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.exceptions import InvalidFormatError
from wiithon.formats.j3danm.j3d import PAD_BYTE, J3DAnmBase, LoopMode


class BVAKeyFrame:
    def __init__(self, show_shape_indices: list[bool]):
        self.show_shape_indices: list[bool] = show_shape_indices


class BVA(J3DAnmBase):
    file_magic: ClassVar[str] = "bva1"
    section_magic: ClassVar[str] = "VAF1"
    section_count: ClassVar[int] = 1


    def __init__(self) -> None:
        self.loop_mode: LoopMode = None
        self.duration: int = 0
        self.keyframes: list[BVAKeyFrame] = []


    @classmethod
    def read(cls, stream: BinaryIO) -> "BVA":
        obj = cls()
        reader = BinaryReader(stream)

        _, section_count = obj.read_header(reader.stream)

        section_start = reader.tell()

        if section_count != obj.section_count:
            raise InvalidFormatError(f"Unexpected section count. Expected {obj.section_count}, got {section_count}.")

        # VAF1 section
        section_magic = reader.string(4)
        if section_magic != obj.section_magic:
            raise InvalidFormatError(f"Invalid file magic, {section_magic!r} instead of {obj.section_magic!r}")

        section_size = reader.u32()
        obj.loop_mode = LoopMode(reader.u8())
        reader.skip(1)
        obj.duration = reader.u16()
        keyframe_count = reader.u16()
        show_count = reader.u16()
        
        # Offsets
        keyframe_offset = reader.u32()
        show_table_offset = reader.u32()

        # Keyframes
        for keyframe_index in range(keyframe_count):
            reader.seek(section_start + keyframe_offset + keyframe_index * 4)
            show_shape_count = reader.u16()
            first_index = reader.u16()

            reader.seek(section_start + show_table_offset + first_index)
            show_shape_indices: list[bool] = []
            for show_shape_index in range(show_shape_count):
                show_shape_indices.append(reader.u8())

            keyframe = BVAKeyFrame(show_shape_indices)
            obj.keyframes.append(keyframe)

        reader.seek(section_start + section_size)

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        file_start = writer.tell()

        self.write_header(writer.stream)

        section_start = writer.tell()

        # VAF1 section
        writer.string(self.section_magic)
        writer.u32(0) # Write the section size later
        writer.u8(self.loop_mode)
        writer.pad(1, PAD_BYTE)
        writer.u16(self.duration)
        writer.u16(len(self.keyframes))

        # Compress the show lists
        seen_show_lists: list[list[bool]] = []
        show_list_offset: list[int] = [0]
        for keyframe in self.keyframes:
            if keyframe.show_shape_indices not in seen_show_lists:
                seen_show_lists.append(keyframe.show_shape_indices)
                show_list_offset.append(len(keyframe.show_shape_indices))

        writer.u16(sum([len(show_list) for show_list in seen_show_lists]))
        
        # Offsets
        writer.u32(0)
        writer.u32(0)
        self.pad_string(writer.stream)

        # Keyframes
        keyframe_offset = writer.tell() - section_start
        for keyframe in self.keyframes:
            writer.u16(len(keyframe.show_shape_indices))
            show_list_index = seen_show_lists.index(keyframe.show_shape_indices)
            writer.u16(show_list_offset[show_list_index])

        # Show table
        show_table_offset = writer.tell() - section_start
        for show_list in seen_show_lists:
            for show in show_list:
                writer.u8(show)

        # Pad table
        self.pad_string(writer.stream, 0x4)

        # Pad section
        self.pad_string(writer.stream)

        section_size = writer.tell() - section_start

        # Write the offsets
        writer.seek(section_start + 0x10)
        writer.u32(keyframe_offset)
        writer.u32(show_table_offset)

        # Section size
        writer.seek(section_start + 0x4)
        writer.u32(section_size)

        # File size
        writer.seek(file_start + 0x8)
        writer.u32(section_start + section_size - file_start)

        writer.seek(section_start + section_size)
