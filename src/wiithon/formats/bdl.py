from io import BytesIO
from typing import BinaryIO
import unittest

from wiithon.binary.align import align
from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.exceptions import InvalidFormatError
from wiithon.formats.bdl_sections.bdl_section import PADDING_STRING, BDLSection, RawSection
from wiithon.formats.bdl_sections.inf1 import INF1Section
from wiithon.formats.bdl_sections.jnt1 import JNT1Section
from wiithon.formats.bdl_sections.tex1 import TEX1Section
# from wiithon.formats.bdl_sections.vtx1 import VTX1Section

J3D_MAGIC = "J3D2"
FILE_MAGIC = "bdl4"
SUBVERSION_MAGIC = "SVR3"

class BDL:
    def __init__(self):
        self.sections: list[BDLSection] = []

    @classmethod
    def read(cls, stream: BinaryIO) -> "BDL":
        obj = cls()
        reader = BinaryReader(stream)

        format_magic = reader.string(4)
        if format_magic != J3D_MAGIC:
            raise InvalidFormatError(f"Invalid magic word for J3D {format_magic:!r} instead of {J3D_MAGIC}")

        file_magic = reader.string(4)
        if file_magic != FILE_MAGIC:
            raise InvalidFormatError(f"Invalid magic word for BDL {file_magic:!r} instead of {FILE_MAGIC}")

        reader.skip(4)
        section_count = reader.u32()

        subversion_magic = reader.string(4)
        if subversion_magic != SUBVERSION_MAGIC:
            raise InvalidFormatError(f"Invalid magic word for subversion {subversion_magic:!r} instead of {SUBVERSION_MAGIC}")

        pad_boundary = align(reader.tell(), 0x20)
        reader.skip(pad_boundary - reader.tell())

        for section_index in range(section_count):
            position = reader.tell()
            section_magic = reader.string(4)
            section_size = reader.u32()

            match section_magic:
                case "INF1":
                    section = INF1Section.read(reader.stream)
                case "JNT1":
                    section = JNT1Section.read(reader.stream)
                case "TEX1":
                    section = TEX1Section.read(reader.stream)
                case _:
                    section = RawSection.read(reader.stream)

            obj.sections.append(section)

            reader.seek(position + section_size)

        return obj

    def get_section(self, section_magic: str) -> BDLSection:
        for section in self.sections:
            if section.magic == section_magic:
                return section

        raise ValueError(f"Section with magic {section_magic} could not be found.")

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        file_start = writer.tell()

        writer.string(J3D_MAGIC)
        writer.string(FILE_MAGIC)
        writer.u32(0) # File size to write later
        writer.u32(len(self.sections))
        writer.string(SUBVERSION_MAGIC)

        pad_boundary = align(writer.tell(), 0x20)
        writer.pad(pad_boundary - writer.tell(), b'\xFF')

        for section in self.sections:
            # Header
            section_start = writer.tell()
            
            writer.string(section.magic)
            writer.u32(0) # Section size to write later

            # Section
            section.write(writer.stream)

            # Tail
            section_end = align(writer.tell(), 0x20)
            pad_size = section_end - writer.tell()
            writer.string(PADDING_STRING[:pad_size])

            # Section size
            writer.seek(section_start + 0x4)
            writer.u32(section_end - section_start)
            writer.seek(section_end)

        writer.seek(file_start + 8)
        writer.u32(section_end - file_start)
        writer.seek(section_end)


class test(unittest.TestCase):
    def test(self):
        with open("C:/Users/sebas/Downloads/powerstar.bdl", 'rb') as f:
            raw_bytes = f.read()

        bdl = BDL.read(BytesIO(raw_bytes))

        write_stream = BytesIO()
        bdl.write(write_stream)

        write_stream.seek(0x0)
        print(write_stream.read(64))
        
        self.assertEqual(raw_bytes, write_stream.getvalue())

if __name__ == "__main__":
    unittest.main()
