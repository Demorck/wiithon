from io import BytesIO
from typing import Callable

from wiithon.file_helper.rarc import Rarc
from wiithon.file_helper.u8 import U8
from wiithon.file_helper.yaz0 import Yaz0


def _split_path(fst, path: str) -> tuple[str, list[str]]:
    parts = [p for p in path.split("/") if p]
    for i in range(len(parts), 0, -1):
        node = fst.find_node(parts[:i])
        if node is not None and node.is_file:
            return "/".join(parts[:i]), parts[i:]
    raise FileNotFoundError(path)

def _open_archive(data: bytes) -> tuple[object, Callable]:
    if data[:4] == b"Yaz0":
        yaz0 = Yaz0.read(BytesIO(data))
        inner, inner_serialize = _open_archive(yaz0.data)
        def yaz0_serialize(arc):
            buf = BytesIO()
            Yaz0.from_data(inner_serialize(arc)).write(buf)
            return buf.getvalue()
        return inner, yaz0_serialize

    if data[:4] == b"RARC":
        arc = Rarc.read(BytesIO(data))
        def serialize(arc):
            buf = BytesIO(); arc.write(buf); return buf.getvalue()
        return arc, serialize

    if data[:4] == b"\x55\xAA\x38\x2D":
        arc = U8.read(BytesIO(data))
        return arc, lambda arc: arc.get_bytes()

    raise ValueError(f"Unknown format: {data[:4]!r}")

def resolve_read(patcher, path: str) -> bytes:
    fst_path, archive_parts = _split_path(patcher.data_partition.fst, path)
    data = patcher.read_file(fst_path)
    if not archive_parts:
        return data
    arc, _ = _open_archive(data)
    return arc.get_file_by_path("/".join(archive_parts))

def resolve_write(patcher, path: str, new_data: bytes) -> None:
    fst_path, archive_parts = _split_path(patcher.data_partition.fst, path)
    if not archive_parts:
        patcher.replace_file(fst_path, new_data)
        return
    data = patcher.read_file(fst_path)
    arc, serialize = _open_archive(data)
    arc.replace_file_by_path("/".join(archive_parts), new_data)
    patcher.replace_file(fst_path, serialize(arc))
