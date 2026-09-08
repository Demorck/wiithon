from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bmg_sections.bmg_section import BMGSection

MID1_MAGIC: str = "MID1"

class MID1Section(BMGSection):
    def __init__(self):
        self.magic = MID1_MAGIC
        self.format: int = 0
        self.info: int = 0
        self.message_ids: list[int] = []
    
    @classmethod
    def read(cls, stream: BinaryIO) -> "MID1Section":
        obj = cls()
        reader = BinaryReader(stream)

        entry_count = reader.u16()
        obj.format = reader.u8()
        obj.info = reader.u8()
        reader.skip(4)
        
        for entry_index in range(entry_count):
            message_id = reader.u32()
            obj.message_ids.append(message_id)

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)
        writer.u16(len(self.message_ids))
        writer.u8(self.format)
        writer.u8(self.info)
        writer.pad(4)
        
        for message_id in self.message_ids:
            writer.u32(message_id)
