from enum import IntEnum
from io import BytesIO
from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.formats.bmg_sections.bmg_section import BMGSection

INF1_MAGIC: str = "INF1"

class CameraType(IntEnum):
    normal = 0
    event = 1
    none = 2

class TalkType(IntEnum):
    normal = 0
    short = 1
    event = 2
    composite = 3
    flow = 4
    null = 5

class BalloonType(IntEnum):
    normal = 0
    unknown = 1
    call = 2
    fixed = 3
    signboard = 4
    info = 5
    icon = 6

class INF1Entry:
    entry_size: int = 0xC

    def __init__(self,
                 message_data_offset: int,
                 camera_ID: int,
                 sound_ID: int,
                 camera_type: CameraType | int,
                 talk_type: TalkType | int,
                 balloon_type: BalloonType | int,
                 area_ID: int,
                 gameeventvalue_index: int):
        
        if not isinstance(camera_type, int) and not isinstance(camera_type, CameraType):
            raise Exception(f"Bad Input camera type: {camera_type}")
        if not isinstance(talk_type, int) and not isinstance(talk_type, TalkType):
            raise Exception(f"Bad Input talk type: {talk_type}")
        if not isinstance(balloon_type, int) and not isinstance(balloon_type, BalloonType):
            raise Exception(f"Bad Input balloon type: {balloon_type}")
        
        self.message_data_offset: int = message_data_offset
        self.camera_ID: int = camera_ID
        self.sound_ID: int = sound_ID
        self.camera_type: CameraType = CameraType(camera_type)
        self.talk_type: TalkType = TalkType(talk_type)
        self.balloon_type: BalloonType = BalloonType(balloon_type)
        self.area_ID: int = area_ID
        self.gameeventvalue_index: int = gameeventvalue_index

    @classmethod
    def import_entry(cls, raw_bytes: BinaryIO) -> "INF1Entry":
        reader = BinaryReader(raw_bytes)
        assert reader.size() == cls.entry_size

        message_data_offset = reader.u32()
        camera_ID = reader.u16()
        sound_ID = reader.u8()
        camera_type = reader.u8()
        talk_type = reader.u8()
        balloon_type = reader.u8()
        area_ID = reader.u8()
        gameeventvalue_index = reader.u8()

        return cls(message_data_offset,
                   camera_ID,
                   sound_ID,
                   camera_type,
                   talk_type,
                   balloon_type,
                   area_ID,
                   gameeventvalue_index)

    def export_entry(self) -> BinaryIO:
        entry_bytes = BytesIO()
        writer = BinaryWriter(entry_bytes)

        writer.u32(self.message_data_offset)
        writer.u16(self.camera_ID)
        writer.u8(self.sound_ID)
        writer.u8(self.camera_type)
        writer.u8(self.talk_type)
        writer.u8(self.balloon_type)
        writer.u8(self.area_ID)
        writer.u8(self.gameeventvalue_index)

        return entry_bytes

class INF1Section(BMGSection):
    """
    Represents an INF1 section from a BMG file.
    This class manages a collection of INF1 entries and provides methods to
    pack and import the section data to/from binary format.
    Attributes:
        data_offset (int): The byte offset where entry data begins (0x8).
        entry_size (int): The size in bytes of each entry (0xC).
        entries (list[INF1Entry]): List of INF1Entry objects in this section.
        entry_count (int): The number of entries in this section.
    Methods:
        __init__(entries): Initialize a new INF1Section with optional entries.
        add_entry(entry): Add an INF1Entry to the section.
        import_section(raw_bytes): Class method to deserialize an INF1 section from raw bytes.
        export_section(): Serialize the section back into binary format.
    """
    data_offset: int = 0x8
    entry_size: int = 0xC
    entries: list[INF1Entry]
    
    def __init__(self, entries: list[INF1Entry] = None):
        super().__init__(INF1_MAGIC)

        # Make sure list is of INF1Entry and set to empty if unspecified
        if entries:
            assert isinstance(entries[0], INF1Entry)
        else:
            entries = []

        self.entry_count = len(entries)
        self.entries = entries
    
    def add_entry(self, entry: INF1Entry):
        """Add an entry to the section"""
        self.entries.append(entry)
        self.entry_count = len(self.entries)

    @classmethod
    def import_section(cls, raw_bytes: BinaryIO) -> "INF1Section":
        """
        Imports a BMG section from raw bytes into an INF1 section object.
        raw_bytes (BytesIO): A BytesIO object containing the section data to import.
        """
        reader = BinaryReader(raw_bytes)
        entry_count = reader.u16()
        entry_size = reader.u16()
        assert entry_size == cls.entry_size

        section = cls()

        for entry_index in range(entry_count):
            raw_bytes.seek(cls.data_offset + entry_index * entry_size)
            entry_bytes: bytes = raw_bytes.read(entry_size)
            entry: INF1Entry = INF1Entry.import_entry(BytesIO(entry_bytes))
            section.add_entry(entry)

        return section

    def export_section(self) -> BinaryIO:
        section_bytes = BytesIO()
        writer = BinaryWriter(section_bytes)

        entry_count = len(self.entries)
        writer.u16(entry_count)
        writer.u16(self.entry_size)
        writer.seek(0x8)
        
        for entry in self.entries:
            entry_data = entry.export_entry()
            writer.raw(entry_data.read)
        
        return section_bytes
