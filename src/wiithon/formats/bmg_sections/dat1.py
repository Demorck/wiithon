from io import BytesIO
from enum import IntEnum
from typing import BinaryIO, NamedTuple

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bmg_sections.bmg_section import BMGSection

DAT1_MAGIC: str = "DAT1"
TAG_IDENTIFIER = b"\x00\x1A"
NULL_BYTE = b"\x00\x00"

class TagIdentifier(IntEnum):
    """
    Identifies when a tag/action will be used when the console displays this in game.
    This can range from delaying more text from appearing, playing a sound effect, coloring text, etc.
    """
    delay = 0x01
    sound_effect = 0x02
    load_image = 0x03
    unknown1 = 0x04
    unknown2 = 0x05
    unknown3 = 0x06
    unknown4 = 0x07
    unknown5 = 0x08
    unknown6 = 0x09
    colour_text = 0xFF

class Tag:
    """
    Container object for one or more tags that will be used within a Message object.
    """
    def __init__(self,
                 offset: int,
                 size: int,
                 identifier: TagIdentifier,
                 data: bytes = None):
        
        if not isinstance(identifier, int) and not isinstance(identifier, TagIdentifier):
            raise Exception("Bad Input")
        
        self.offset: int = offset
        self.size: int = size
        self.identifier: TagIdentifier = TagIdentifier(identifier)
        self.data = data

    @classmethod
    def import_tag(cls, raw_bytes: BinaryIO, offset: int) -> "Tag":
        reader = BinaryReader(raw_bytes)
        size = reader.u8()
        identifier = reader.raw(1)
        data = reader.raw(size - 4)

        return cls(offset, size, identifier, data)

    def export_tag(self) -> BinaryIO:
        assert isinstance(self.data, bytes)
        tag_bytes: BytesIO = BytesIO()
        writer = BinaryWriter(tag_bytes)

        writer.raw(TAG_IDENTIFIER)
        writer.u8(self.size)
        writer.u8(self.identifier)
        writer.raw(self.data)

        return tag_bytes

class Message(NamedTuple):
    """
    The collection of a single or multi-lined message that will be displayed in an event, sign, message bubble, etc.
    This also contains the list of actions/tags that will occur with the given message.
    """
    string: str
    tags: list[Tag]

class DAT1Section(BMGSection):
    """
    Represents a section of DAT1 message data containing multiple messages with their associated tags.
    This class handles the serialization and deserialization of message sections encoded in a binary format
    that combines UTF-8/Shift-JIS encoded text with embedded tag markers. Messages are delimited by null
    characters and can contain formatting or metadata tags at various offsets within the string.
    Attributes:
        messages (list[Message]): A list of Message objects contained in this section.
    """
    def __init__(self, messages: list[Message] = None):
        super().__init__(DAT1_MAGIC)

        if messages == None:
            messages = []
        self.messages: list[Message] = messages
    
    def add_message(self, message: Message):
        self.messages.append(message)
    
    @classmethod
    def import_section(cls, raw_bytes: BinaryIO):
        reader = BinaryReader(raw_bytes)
        section = cls()

        string = ''
        tags: list[Tag] = []
        
        while reader.tell() < reader.size():
            char_bytes = reader.raw(2)
            if char_bytes == TAG_IDENTIFIER: # Found a tag
                offset = len(string)
                tag = Tag.import_tag(raw_bytes, offset)
                tags.append(tag)
            else:
                int_value = int.from_bytes(char_bytes)
                string += chr(int_value)
            
            if char_bytes == NULL_BYTE: # Reading a null character
                message = Message(string, tags)
                section.add_message(message)
                
                string = ''
                tags = []
        
        return section
        
    def export_section(self) -> BinaryIO:
        """
        Export message section by serializing messages with their tags and characters into binary data.
        Iterates through each message's characters and associated tags, writing tag data before each character
        and any closing tags at the end of the string, encoding characters in Shift-JIS format.
        """
        data = BytesIO()
        writer = BinaryWriter(data)

        for message in self.messages:
            string = message.string
            tags = message.tags

            offset = -1
            for offset, char in enumerate(string):
                current_tags = [tag for tag in tags if tag.offset == offset]
                for tag in current_tags:
                    tag_data = tag.export_tag()
                    writer.raw(tag_data.read())

                writer.string(char, 2)
            
            if not string:
                writer.raw(NULL_BYTE)

            # Since message.string does not contains the tags themselves, we must also check to see if there are tags at the end of the string
            closing_tags = [tag for tag in tags if tag.offset == offset + 1]
            for tag in closing_tags:
                tag_data = tag.export_tag()
                writer.raw(tag_data.read)
                
        return data
