from typing import BinaryIO, Optional


class IOWindow:
    """I/O sub-window over a seekable binary stream"""
    def __init__(self, stream: BinaryIO, start: int, length: Optional[int] = None) -> None:
        self.stream = stream
        self.start = start
        self.length = length
        self.pos = 0

    def read(self, n: int) -> bytes:
        """
        Read n bytes from stream at the current position.

        :param n: `int` - Number of bytes to read
        :return: `bytes` - Bytes read from the stream
        """
        if self.length is not None:
            n = min(n, self.length - self.pos)
        if n <= 0:
            return b''

        self.stream.seek(self.start + self.pos)
        data: bytes = self.stream.read(n)
        self.pos += len(data)

        return data

    def write(self, data: bytes) -> int:
        """
        Write bytes to stream at the current position.

        :param data: `bytes` - Bytes to write
        :return: `None`
        """
        if self.length is not None:
            data = data[:self.length - self.pos]

        self.stream.seek(self.start + self.pos)
        written = self.stream.write(data)
        self.pos += written

        return written

    def seek(self, offset: int, whence: Optional[int] = 0) -> int:
        """
        Get to the position, depending on whence.

        :param offset: `int` - Position to seek
        :param whence: `int` - Seek position.
            - 0 = from start,
            - 1 = from current position
            - 2 = from end
        :return: `int` - Position
        """
        if whence is None:
            whence = 0

        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        elif whence == 2:
            if self.length is None:
                raise ValueError("IOWindow: no length, impossible to seek")

            self.pos = self.length + offset

        return self.pos

    def tell(self) -> int:
        """
        Get the current position.
        :return: `int` - Position
        """
        return self.pos