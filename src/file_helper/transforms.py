from io import BytesIO
from typing import Callable
from file_helper.yaz0 import Yaz0
from file_helper.rarc import Rarc

def yaz0_transform(inner: Callable[[bytes], bytes]) -> Callable[[bytes], bytes]:
    def transform(data: bytes) -> bytes:
        yaz0 = Yaz0.read(BytesIO(data))
        result = inner(yaz0.data)
        buffer = BytesIO()
        Yaz0.from_data(result).write(buffer)
        return buffer.getvalue()

    return transform

def auto_yaz0_transform(inner: Callable[[bytes], bytes]) -> Callable[[bytes], bytes]:
    def transform(data: bytes) -> bytes:
        if data[:4] == b"Yaz0":
            return yaz0_transform(inner)(data)

        return inner(data)

    return transform

def rarc_transform(inner: Callable[[Rarc], None]) -> Callable[[bytes], bytes]:
    def transform(data: bytes) -> bytes:
        rarc = Rarc.read(BytesIO(data))
        inner(rarc)
        buf = BytesIO()
        rarc.write(buf)
        return buf.getvalue()
    return transform