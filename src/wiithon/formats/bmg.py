from io import BytesIO
from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bmg_sections.bmg_section import BMGSection
from wiithon.formats.bmg_sections.inf1 import INF1Section
from wiithon.formats.bmg_sections.dat1 import DAT1Section
from wiithon.formats.bmg_sections.flw1 import FLW1Section
from wiithon.formats.bmg_sections.fli1 import FLI1Section

DATA_MAGIC = "MESG"
FILE_MAGIC = "bmg1"

class BMG:
    """
    BMG (Binary Message Data) file handler for parsing and exporting binary message data.
    The BMG class manages the structure of BMG files which contain multiple sections
    (INF1, DAT1, FLW1, FLI1) that store message information and data.
    Attributes:
        section_count (int): Number of sections in the BMG file.
        sections (list[bmg_section]): List of parsed section objects.
        flw1_section_offset (int): Offset to the FLW1 section in the file.
        unknown (int): Unknown single byte value from file header.
    Methods:
        __init__(raw_bytes: BytesIO) -> None:
            Parses a BMG file from raw bytes. Validates magic numbers and reads
            all sections from the file.
        add_header(section: bmg_section) -> BytesIO:
            Wraps a section with its BMG header (magic and size) and applies
            32-byte alignment padding. Returns the complete section data.
        export_bmg() -> BytesIO:
            Reconstructs the complete BMG file from the current sections list.
            Rebuilds the header and all sections with proper formatting and padding.
            Returns the complete BMG file as bytes.
    """
    section_count: int
    sections: list[BMGSection]

    def __init__(self, raw_bytes: BinaryIO):
        reader = BinaryReader(raw_bytes)
        data_magic = reader.string(0x4)
        assert data_magic == DATA_MAGIC

        file_magic = reader.string(0x4)
        assert file_magic == FILE_MAGIC

        self.flw1_section_offset = reader.u32()
        self.section_count = reader.u32()
        self.unknown = reader.u8()
        reader.seek(0x20)

        self.sections = []

        for section in range(self.section_count):
            section_magic = reader.string(0x4)
            section_size = reader.u32() - 0x8

            # Take into account the removed padding at the end of the file
            if section_size > reader.size() - reader.tell():
                section_size = reader.size() - reader.tell()

            section_bytes = reader.raw(section_size)
            section_bytes = BytesIO(section_bytes)
            
            match section_magic:
                case "INF1":
                    section = INF1Section.import_section(section_bytes)
                case "DAT1":
                    section = DAT1Section.import_section(section_bytes)
                case "FLW1":
                    section = FLW1Section.import_section(section_bytes)
                case "FLI1":
                    section = FLI1Section.import_section(section_bytes)
            
            self.sections.append(section)

    def add_header(self, section: BMGSection) -> BinaryIO:
        total_bytes = BytesIO()
        writer = BinaryWriter(total_bytes)

        section_bytes = section.export_section()
        section_size = section_bytes.seek(0, 2) + 0x8
        
        padding = 0
        if section_size % 32:
            padding = 32 - section_size % 32
            section_size += padding

        writer.string(section.magic, 0x4)
        writer.u32(section_size)
        writer.raw(section_bytes.read)
        writer.pad(padding) # should be align(0x20)

        return total_bytes
    
    def get_section(self, section_magic: str) -> list[BMGSection]:
        out: list[BMGSection] = []

        for section in self.sections:
            if section.magic == section_magic:
                out.append(section)
        
        return out

    def export_bmg(self) -> BinaryIO:
        bmg_bytes = BytesIO()
        writer = BinaryWriter(bmg_bytes)

        writer.string(DATA_MAGIC)
        writer.string(FILE_MAGIC)
        writer.u32(0) # Write the flw1_section_offset later
        writer.u32(len(self.sections))
        writer.u8(self.unknown)
        writer.seek(0x20)

        for section in self.sections:
            if section.magic == "FLW1":
                position = writer.tell()
                writer.seek(0x8)
                writer.u32(position)
                writer.seek(position)
            
            section_bytes = self.add_header(section)
            writer.raw(section_bytes.read())

        return bmg_bytes
