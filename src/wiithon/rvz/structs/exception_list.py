from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.rvz.structs.exception import WiaException


class WiaExceptionList:
    def __init__(self) -> None:
        """
        Constructor
        """
        #: Every exception to apply, in order of the image stores them
        self.exceptions: list[WiaException] = []

    def __len__(self) -> int:
        return len(self.exceptions)

    @classmethod
    def read(cls, stream: BinaryIO) -> 'WiaExceptionList':
        """
        Read an exception list

        Args:
            stream: Current stream of the file

        Returns:
            The object created
        """
        obj = cls()
        number_of_exceptions = BinaryReader(stream).u16()
        obj.exceptions = [ WiaException.read(stream) for _ in range(number_of_exceptions) ]

        return obj