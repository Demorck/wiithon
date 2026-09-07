from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bmg_sections.bmg_section import BMGSection

FLI1_MAGIC: str = "FLI1"

class FLI1Section(BMGSection):
    def __init__(self) -> None:
        self.magic = FLI1_MAGIC
        self.entries: list[bytes] = []
        self.entry_size: int = 0
        
    @classmethod
    def read(cls, stream: BinaryIO) -> "FLI1Section":
        obj = cls()
        reader = BinaryReader(stream)

        entry_count = reader.u16()
        obj.entry_size = reader.u8()
        reader.skip(5)

        for entry_index in range(entry_count):
            entry = reader.raw(obj.entry_size)
            obj.entries.append(entry)

        return obj
    
    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.u16(len(self.entries))
        writer.u8(self.entry_size)
        writer.pad(5)

        for entry in self.entries:
            writer.raw(entry)
