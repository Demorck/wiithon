from helpers.Utils import *

class TMDContent:
    """
    Content Metadata (CMD) from TMD (Title Metadata)
    https://wiibrew.org/wiki/Title_metadata
    -----------------------------------------
    Offset  Taille         Field
    0x00   0x04            Content ID
    0x04   0x02            Index
    0x06   0x02            Type (0x0001: Normal, 0x4001: DLC, 0x8001: Shared)
    0x08   0x08            Size
    0x10   0x14            SHA1 Hash
    """
    def __init__(self) -> None:
        self.id: int = 0
        self.index: int = 0
        self.content_type: int = 0
        self.size: int = 0
        self.hash: bytes = b'\x00' * 0x14


    @classmethod
    def read(cls, stream: BinaryIO) -> 'TMDContent':
        """
        Read and parse a CMD from a binary stream
        :param stream: Binary IO stream
        :return: TMDContent
        """
        obj = cls()

        obj.id              = read_u32(stream)
        obj.index           = read_u16(stream)
        obj.content_type    = read_u16(stream)
        obj.size            = read_u64(stream)
        obj.hash            = stream.read(0x14)

        return obj

    def write(self, stream: BinaryIO) -> None:
        """
        Write content to a binary stream
        :param stream: Binary IO stream
        :return: None
        """
        stream.write(struct.pack('>I', self.id))
        stream.write(struct.pack('>H', self.index))
        stream.write(struct.pack('>H', self.content_type))
        stream.write(struct.pack('>Q', self.size))
        stream.write(self.hash)