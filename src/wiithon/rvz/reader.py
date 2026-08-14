from typing import BinaryIO
from wiithon.rvz.structs.file_header import WiaHeader


class WiaReader:
    """
    Reads the structure of a WIA or RVZ image

    Mimic the WiiIsoReader
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self.file: BinaryIO = open(path, "rb")

        try:
            self.header: WiaHeader = WiaHeader.read(self.file)
        except BaseException:
            self.file.close()
            raise


    def close(self) -> None:
        self.file.close()

    def __enter__(self) -> "WiaReader":
        return self

    def __exit__(self, *args) -> None:
        self.close()