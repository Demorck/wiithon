from typing import BinaryIO, NamedTuple

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bmg_sections.bmg_section import BMGSection

DAT1_MAGIC: str = "DAT1"
TAG_IDENTIFIER = b"\x00\x1A"
NULL_BYTE = b"\x00\x00"

class Tag:
    offset: int

    def __init__(self) -> None:
        self.offset: int = 0 # Not a value thats read
        self.size: int = 0
        self.identifier: int = 0
        self.data: bytes = b''

    @classmethod
    def read(cls, stream: BinaryIO) -> "Tag":
        obj = cls()
        reader = BinaryReader(stream)

        obj.size = reader.u8()
        obj.identifier = reader.u8()
        obj.data = reader.raw(obj.size - 4)

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.raw(TAG_IDENTIFIER)
        writer.u8(self.size)
        writer.u8(self.identifier)
        writer.raw(self.data)

class Message(NamedTuple):
    string: str
    tags: list[Tag]

class DAT1Section(BMGSection):
    def __init__(self) -> None:
        self.magic = DAT1_MAGIC
        self.messages: list[Message] = []
    
    @classmethod
    def read(cls, stream: BinaryIO) -> "DAT1Section":
        obj = cls()
        reader = BinaryReader(stream)

        reader.seek(-4, 1)
        size = reader.u32()
        start = reader.tell() - 8

        string = ''
        tags: list[Tag] = []

        while reader.tell() < start + size:
            char_bytes = reader.raw(2)
            if char_bytes == TAG_IDENTIFIER: # Found a tag
                tag = Tag.read(stream)
                tag.offset = len(string)
                tags.append(tag)

                continue
        
            int_value = int.from_bytes(char_bytes)
            string += chr(int_value)
            
            if char_bytes == NULL_BYTE: # Reading a null character
                message = Message(string, tags)
                obj.messages.append(message)
                
                string = ''
                tags = []

        return obj
        
    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        for message in self.messages:
            string = message.string
            
            if not string:
                writer.raw(NULL_BYTE)
                continue

            for offset, char in enumerate(string):
                current_tags = [tag for tag in message.tags if tag.offset == offset]
                for tag in current_tags:
                    tag.write(writer.stream)

                writer.u16(ord(char))
            else:
                # Since message.string does not contains the tags themselves, we must also check to see if there are tags at the end of the string
                closing_tags = [tag for tag in message.tags if tag.offset == offset + 1]
                for tag in closing_tags:
                    tag.write(writer.stream)
