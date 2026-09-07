from abc import ABC, abstractmethod
from typing import BinaryIO, ClassVar

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter

class BMGSection(ABC):
    magic: ClassVar[str]

    @classmethod
    @abstractmethod
    def read(cls, stream: BinaryIO) -> "BMGSection":
        """Read a section from a data stream."""

    @abstractmethod
    def write(self, stream: BinaryIO) -> None:
        """Write a section to a data stream."""

# Default section
class RawSection(BMGSection):
    data: bytes

    def __init__(self):
        self.data = b''

    @classmethod
    def read(cls, stream: BinaryIO) -> "RawSection":
        obj = cls()
        reader = BinaryReader(stream)
        obj.data = reader.raw()

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)
        writer.raw(self.data)
