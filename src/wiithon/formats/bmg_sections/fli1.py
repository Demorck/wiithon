from io import BytesIO
from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bmg_sections.bmg_section import BMGSection

FLI1_MAGIC: str = "FLI1"

class FLI1Entry:
    def __init__(self, unknown1: int, unknown2: int):
        self.unknown1 = unknown1
        self.unknown2 = unknown2

    def export_entry(self) -> BinaryIO:
        entry_bytes = BytesIO()
        writer = BinaryWriter(entry_bytes)

        writer.u16(self.unknown1)
        writer.u16(0)
        writer.u16(self.unknown2)
        writer.u16(0)

        return entry_bytes

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
    def import_section(cls, raw_bytes: BinaryIO):
        reader = BinaryReader(raw_bytes)

        entry_count = reader.u16()
        entry_size = reader.u8()
        reader.skip(0x1)

        assert entry_size == cls.entry_size

        section = cls()

        for entry_index in range(entry_count):
            unknown1 = reader.u16()
            reader.skip(0x2)
            unknown2 = reader.u16()
            reader.skip(0x2)

            entry = FLI1Entry(unknown1, unknown2)
            section.add_entry(entry)
        
        return section
    
    def export_section(self) -> BinaryIO:
        section_bytes = BytesIO()
        writer = BinaryWriter(section_bytes)

        self.entry_count = len(self.entries)
        writer.u16(self.entry_count)
        writer.u8(self.entry_size)
        writer.seek(0x8)

        for entry in self.entries:
            entry_data = entry.export_entry()
            writer.raw(entry_data.read)

        return section_bytes
