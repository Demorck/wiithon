from typing import BinaryIO

from wiithon.binary.align import align
from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.exceptions import InvalidFormatError
from wiithon.formats.bmg_sections.bmg_section import BMGSection, RawSection
from wiithon.formats.bmg_sections.inf1 import INF1Section
from wiithon.formats.bmg_sections.dat1 import DAT1Section
from wiithon.formats.bmg_sections.mid1 import MID1Section
from wiithon.formats.bmg_sections.flw1 import FLW1Section
from wiithon.formats.bmg_sections.fli1 import FLI1Section

DATA_MAGIC = "MESG"
FILE_MAGIC = "bmg1"

class BMG:
    def __init__(self) -> None:
        self.sections: list[BMGSection] = []
        self.end_of_message_data: int = 0
        self.encoding: int = 0

    @classmethod
    def read(cls, stream: BinaryIO) -> "BMG":
        obj = cls()
        reader = BinaryReader(stream)

        data_magic = reader.string(0x4)
        if data_magic != DATA_MAGIC:
            raise InvalidFormatError(f"Invalid magic data word for BMG {data_magic:!r} instead of {DATA_MAGIC}")

        file_magic = reader.string(0x4)
        if file_magic != FILE_MAGIC:
            raise InvalidFormatError(f"Invalid magic file word for BMG {file_magic:!r} instead of {FILE_MAGIC}")

        obj.end_of_message_data = reader.u32()

        section_count = reader.u32()

        obj.encoding = reader.u8()
        reader.seek(0x20)

        for section in range(section_count):
            position = reader.tell()
            section_magic = reader.string(0x4)
            section_size = reader.u32()
            
            match section_magic:
                case "INF1":
                    section = INF1Section.read(reader.stream)
                case "DAT1":
                    section = DAT1Section.read(reader.stream)
                case "MID1":
                    section = MID1Section.read(reader.stream)
                case "FLW1":
                    section = FLW1Section.read(reader.stream)
                case "FLI1":
                    section = FLI1Section.read(reader.stream)
                case _:
                    section = RawSection.read(reader.stream)
                    
            obj.sections.append(section)

            reader.seek(position + section_size)

        return obj

    def get_section(self, section_magic: str) -> BMGSection:
        for section in self.sections:
            if section.magic == section_magic:
                return section

        raise ValueError(f"Section with magic {section_magic} could not be found")

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.string(DATA_MAGIC)
        writer.string(FILE_MAGIC)
        writer.u32(0) # Write the end_of_message_data later
        writer.u32(len(self.sections))
        writer.u8(self.encoding)

        pad_boundary = align(writer.tell(), 0x20)
        writer.pad(pad_boundary - writer.tell())

        for section in self.sections:
            if section.magic == "FLW1" or section.magic == "MID1":
                position = writer.tell()
                
                writer.seek(0x8)
                writer.u32(position)
                writer.seek(position)

            # Header
            section_start = writer.tell()

            writer.string(section.magic)
            writer.u32(0) # Write the section size later

            # Section
            section.write(writer.stream)

            section_end = writer.tell()

            # Tail
            pad_boundary = align(writer.tell(), 0x20)
            writer.pad(pad_boundary - writer.tell())

            # Section size
            position = writer.tell()
            
            writer.seek(section_start + 0x4)
            writer.u32(position - section_start)
            writer.seek(position)

        writer.truncate(section_end)
