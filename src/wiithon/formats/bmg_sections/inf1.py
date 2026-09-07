from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bmg_sections.bmg_section import BMGSection

INF1_MAGIC: str = "INF1"

class INF1Entry:
    def __init__(self):
        self.offset: int = 0
        self.data: bytes = b''

    @classmethod
    def read(cls, stream: BinaryIO, entry_size: int) -> "INF1Entry":
        obj = cls()
        reader = BinaryReader(stream)

        obj.offset = reader.u32()
        obj.data = reader.raw(entry_size - 4)

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.u32(self.offset)
        writer.raw(self.data)

class INF1Section(BMGSection):
    def __init__(self):
        self.magic = INF1_MAGIC
        self.entries: list[INF1Entry] = []
        self.entry_size: int = 0
        self.group_id: int = 0
        self.default_colour_index: int = 0
    
    @classmethod
    def read(cls, stream: BinaryIO) -> "INF1Section":
        obj = cls()
        reader = BinaryReader(stream)
        
        entry_count = reader.u16()
        obj.entry_size = reader.u16()
        obj.group_id = reader.u16()
        obj.default_colour_index = reader.u8()
        reader.skip(1)
        
        for entry_index in range(entry_count):
            entry = INF1Entry.read(reader.stream, obj.entry_size)
            obj.entries.append(entry)
    
        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)
        
        writer.u16(len(self.entries))
        writer.u16(self.entry_size)
        writer.u16(self.group_id)
        writer.u8(self.default_colour_index)
        writer.pad(1)
        
        for entry in self.entries:
            entry.write(writer.stream)
