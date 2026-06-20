from io import BytesIO
import wiithon.helpers.Utils as fh
from wiithon.file_helper.bmg_sections.bmg_section import BMGSection

FLI1_MAGIC: str = "FLI1"

class FLI1Entry:
    def __init__(self, unknown1: int, unknown2: int):
        self.unknown1 = unknown1
        self.unknown2 = unknown2

    def export_entry(self) -> BytesIO:
        data = BytesIO()

        fh.write_u16(data, self.unknown1, 0x0)
        fh.write_u16(data, 0, 0x2)
        fh.write_u16(data, self.unknown2, 0x4)
        fh.write_u16(data, 0, 0x6)

        return data

class FLI1Section(BMGSection):
    """
    A section containing a collection of FLI1 entries.
    This class manages a list of FLI1Entry objects and provides functionality to serialize
    and deserialize them to/from binary data. Each entry has a fixed size of 0x8 bytes.
    Attributes:
        entry_size (int): The fixed size of each FLI1Entry in bytes (0x8).
        entry_count (int): The current number of entries in the section.
        entries (list[FLI1Entry]): The list of FLI1Entry objects contained in this section.
    Methods:
        __init__(entries): Initializes a new FLI1Section with an optional list of entries.
        add_entry(entry): Adds a new FLI1Entry to the section and updates the entry count.
        import_section(raw_bytes): Class method that deserializes binary data into a FLI1Section object.
        export_section(): Serializes the section and its entries back into binary data.
    """
    entry_size = 0x8

    def __init__(self, entries: list[FLI1Entry] = None):
        super().__init__(FLI1_MAGIC)

        if entries == None:
            entries = []

        self.entry_count = len(entries)
        self.entries = entries

    def add_entry(self, entry: FLI1Entry):
        self.entries.append(entry)
        self.entry_count = len(self.entries)

    @classmethod
    def import_section(cls, raw_bytes: BytesIO):
        entry_count = fh.read_u16(raw_bytes, 0x0)
        entry_size = fh.read_u8(raw_bytes, 0x2)
        assert entry_size == cls.entry_size

        section = cls()

        offset = 0x8
        for entry_index in range(entry_count):
            unknown1 = fh.read_u16(raw_bytes, offset)
            unknown2 = fh.read_u16(raw_bytes, offset + 0x4)

            entry = FLI1Entry(unknown1, unknown2)
            section.add_entry(entry)
            
            offset += entry_size
        
        return section
    
    def export_section(self) -> BytesIO:
        data = BytesIO()

        self.entry_count = len(self.entries)
        fh.write_u16(data, self.entry_count, 0x0)
        fh.write_u8(data, self.entry_size, 0x2)
        fh.write_bytes(data, b'\x00' * 5, 0x3)

        offset = 0x8
        for entry in self.entries:
            entry_data = entry.export_entry()
            fh.write_bytes(data, entry_data.getvalue(), offset)

            offset += 0x8

        return data
