from abc import ABC, abstractmethod
from io import BytesIO

class BMGSection(ABC):
    """
    Base class for BMG file sections.
    Provides the interface for importing and exporting binary section data.
    Subclasses must override import_section() and export_section() methods.
    Attributes:
        magic (str): The magic identifier for this section type.
    """
    magic: str

    def __init__(self, magic: str):
        self.magic = magic

    @classmethod
    @abstractmethod
    def import_section(cls, raw_bytes: BytesIO) -> "BMGSection":
        """
        Import a section from raw bytes.
        This method must be overridden in subclasses to provide proper implementation.
        Raises NotImplementedError: If not properly overridden in a subclass.
        """
        raise NotImplementedError("Import section is not implemented")

    @abstractmethod
    def export_section(self) -> BytesIO:
        """
        Export a section from raw bytes.
        This method must be overridden in subclasses to provide proper implementation.
        Raises NotImplementedError: If not properly overridden in a subclass.
        """
        raise NotImplementedError("Export section is not implemented")
