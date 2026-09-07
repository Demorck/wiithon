from abc import ABC, abstractmethod
from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter

class BMGSection(ABC):
    """
    Base class for BMG file sections.
    Provides the interface for importing and exporting binary section data.
    Subclasses must override import_section() and export_section() methods.
    Attributes:
        magic (str): The magic identifier for this section type.
    """
    magic: str

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
