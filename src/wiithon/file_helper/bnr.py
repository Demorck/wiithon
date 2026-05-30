import struct
from io import BytesIO
from typing import BinaryIO
from wiithon.structs.IMET import IMET


class BNR:
    def __init__(self):
        self.imet: IMET = IMET()
        self._inner_data: bytes = b""

    @classmethod
    def read(cls, stream: BinaryIO) -> "BNR":
        obj = cls()
        obj.imet = IMET.read(stream)

        # start of U8 archive
        obj._inner_data = stream.read()
        return obj

    def write(self, stream: BinaryIO) -> None:
        self.imet.write(stream)
        stream.write(self._inner_data)

    @property
    def title(self) -> str:
        return self.imet.get_title(1)

    def get_bytes(self) -> bytes:
        buf = BytesIO()
        self.write(buf)
        return buf.getvalue()

    def __repr__(self) -> str:
        return f"BNR title={self.title!r}\n{self.imet}"
