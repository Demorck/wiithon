from io import BytesIO

import wiithon.helpers.Utils as fh
from wiithon.file_helper.bmg_sections.bmg_section import BMGSection
from wiithon.file_helper.bmg_sections.inf1 import INF1Section
from wiithon.file_helper.bmg_sections.dat1 import DAT1Section
from wiithon.file_helper.bmg_sections.flw1 import FLW1Section
from wiithon.file_helper.bmg_sections.fli1 import FLI1Section

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
        add_header_to_section(section: bmg_section) -> BytesIO:
            Wraps a section with its BMG header (magic and size) and applies
            32-byte alignment padding. Returns the complete section data.
        export_bmg() -> BytesIO:
            Reconstructs the complete BMG file from the current sections list.
            Rebuilds the header and all sections with proper formatting and padding.
            Returns the complete BMG file as bytes.
    """
    section_count: int
    sections: list[BMGSection]

    def __init__(self, raw_bytes: BytesIO):
        data_magic = fh.read_string(raw_bytes, 4, 0x0)
        assert data_magic == "MESG"

        file_magic = fh.read_string(raw_bytes, 4, 0x4)
        assert file_magic == "bmg1"

        self.flw1_section_offset = fh.read_u32(raw_bytes, 0x8)
        self.section_count = fh.read_u32(raw_bytes, 0xC)
        self.unknown = fh.read_u8(raw_bytes, 0x10)
        # 15 bytes of padding

        self.sections = []

        offset = 0x20
        for section in range(self.section_count):
            section_magic = fh.read_string(raw_bytes, 4, offset)
            section_size = fh.read_u32(raw_bytes, offset + 0x4) - 0x8
            offset += 8
            
            raw_bytes.seek(offset, 0)
            section_bytes = raw_bytes.read(section_size)
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
            offset += section_size

    def add_header_to_section(self, section: BMGSection) -> BytesIO:
        data = BytesIO()

        section_bytes = section.export_section()
        section_size = section_bytes.seek(0, 2) + 0x8
        
        padding = 0
        if section_size % 32:
            padding = 32 - section_size % 32
            section_size += padding
        
        fh.write_str(data, section.magic, 4, offset=0x0)
        fh.write_u32(data, section_size, 0x4)
        fh.write_bytes(data, section_bytes.getvalue(), 0x8)
        fh.write_bytes(data, b'\x00' * padding, section_size - padding)

        return data
    
    def get_section(self, section_magic: str) -> list[BMGSection]:
        out: list[BMGSection] = []

        for section in self.sections:
            if section.magic == section_magic:
                out.append(section)
        
        return out

    def export_bmg(self) -> BytesIO:
        data = BytesIO()

        fh.write_str(data, "MESG", 4, offset=0x0)
        fh.write_str(data, "bmg1", 4, offset=0x4)
        fh.write_u32(data, 0, 0x8) # Write the flw1_section_offset later
        fh.write_u32(data, len(self.sections), 0xC)
        fh.write_u8(data, self.unknown, 0x10)
        fh.write_bytes(data, b'\x00' * 15, 0x11)

        offset = 0x20
        for section in self.sections:
            if section.magic == "FLW1":
                fh.write_u32(data ,offset, 0x8)
            
            section_bytes = self.add_header_to_section(section)
            fh.write_bytes(data, section_bytes.getvalue(), offset)
            offset += len(section_bytes.getvalue())

        return data
