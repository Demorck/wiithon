from typing import BinaryIO

from wiithon.binary.align import align
from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bdl_sections.bdl_section import BDLSection, PADDING_STRING

JNT1_MAGIC = "JNT1"

class Joint:
    name: str
    remap_index: int

    def __init__(self) -> None:
        self.name: str = ''
        self.remap_index: int = 0

        self.matrix_type: int = 0
        self.ignore_parent_scale: bool = False
        self.scale_x: float = 0.0
        self.scale_y: float = 0.0
        self.scale_z: float = 0.0
        self.rotation_x: int = 0
        self.rotation_y: int = 0
        self.rotation_z: int = 0
        self.translation_x: float = 0.0
        self.translation_y: float = 0.0
        self.translation_z: float = 0.0
        self.bounding_sphere_radius: float = 0.0
        self.bounding_box_min_x: float = 0.0
        self.bounding_box_min_y: float = 0.0
        self.bounding_box_min_z: float = 0.0
        self.bounding_box_max_x: float = 0.0
        self.bounding_box_max_y: float = 0.0
        self.bounding_box_max_z: float = 0.0

    @classmethod
    def read(cls, stream: BinaryIO) -> "Joint":
        obj = cls()
        reader = BinaryReader(stream)

        obj.matrix_type = reader.u16()
        obj.ignore_parent_scale = reader.u8()
        reader.skip(1)
        obj.scale_x = reader.float()
        obj.scale_y = reader.float()
        obj.scale_z = reader.float()
        obj.rotation_x = reader.s16()
        obj.rotation_y = reader.s16()
        obj.rotation_z = reader.s16()
        reader.skip(2)
        obj.translation_x = reader.float()
        obj.translation_y = reader.float()
        obj.translation_z = reader.float()
        obj.bounding_sphere_radius = reader.float()
        obj.bounding_box_min_x = reader.float()
        obj.bounding_box_min_y = reader.float()
        obj.bounding_box_min_z = reader.float()
        obj.bounding_box_max_x = reader.float()
        obj.bounding_box_max_y = reader.float()
        obj.bounding_box_max_z = reader.float()

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.u16(self.matrix_type)
        writer.u8(self.ignore_parent_scale)
        writer.pad(1, b'\xFF')
        writer.float(self.scale_x)
        writer.float(self.scale_y)
        writer.float(self.scale_z)
        writer.s16(self.rotation_x)
        writer.s16(self.rotation_y)
        writer.s16(self.rotation_z)
        writer.pad(2, b'\xFF')
        writer.float(self.translation_x)
        writer.float(self.translation_y)
        writer.float(self.translation_z)
        writer.float(self.bounding_sphere_radius)
        writer.float(self.bounding_box_min_x)
        writer.float(self.bounding_box_min_y)
        writer.float(self.bounding_box_min_z)
        writer.float(self.bounding_box_max_x)
        writer.float(self.bounding_box_max_y)
        writer.float(self.bounding_box_max_z)

class JNT1Section(BDLSection):
    def __init__(self) -> None:
        self.magic = JNT1_MAGIC

        self.joints: list[Joint] = []

    @classmethod
    def read(cls, stream: BinaryIO) -> "JNT1Section":
        obj = cls()
        reader = BinaryReader(stream)

        section_start = reader.tell() - 8

        joint_count = reader.u16()
        reader.skip(2)
        joint_transform_table_offset = reader.u32()
        remap_table_offset = reader.u32()
        name_table_offset = reader.u32()

        reader.seek(section_start + joint_transform_table_offset)

        for joint_index in range(joint_count):
            joint = Joint.read(reader.stream)
            obj.joints.append(joint)

        reader.seek(section_start + remap_table_offset)

        for joint in obj.joints:
            joint.remap_index = reader.u16()
        
        reader.seek(section_start + name_table_offset)

        joint_names = obj.read_string_table(reader.stream)

        for name, joint in zip(joint_names, obj.joints):
            joint.name = name

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        section_start = writer.tell() - 8

        writer.u16(len(self.joints))
        writer.pad(2, b'\xFF')

        # Offsets to be written later
        writer.u32(0)
        writer.u32(0)
        writer.u32(0)

        joint_transform_table_offset = writer.tell() - section_start

        for joint in self.joints:
            joint.write(writer.stream)

        remap_table_offset = writer.tell() - section_start

        for joint in self.joints:
            writer.u16(joint.remap_index)


        joint_names = [joint.name for joint in self.joints]

        if joint_names:
            pad_boundary = align(writer.tell(), 0x20)
            pad_size = pad_boundary - writer.tell()
            writer.string(PADDING_STRING[:pad_size])

            self.write_string_table(writer.stream, joint_names)

            name_table_offset = pad_boundary - section_start
        else:
            name_table_offset = 0

        position = writer.tell()

        writer.seek(section_start + 0xC)
        writer.u32(joint_transform_table_offset)
        writer.u32(remap_table_offset)
        writer.u32(name_table_offset)
        
        writer.seek(position)
