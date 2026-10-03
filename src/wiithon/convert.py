from wiithon.exceptions import InvalidFormatError
from wiithon.output import IsoOutput
from wiithon.rvz.layout import RVZ_MAGIC_WORD, WIA_MAGIC_WORD
from wiithon.rvz.reader import WiaReader
from wiithon.rvz.rebuilder import IsoRebuilder


def convert(source: str, destination: str, output: IsoOutput) -> None:
    """
    Convert a disc image into another container

    The output format is named. The input one is readed by magic word

    Args:
        source: Path to the image to read
        destination: Path to write
        output: What to write

    Raises:
        InvalidFormatError: If the source is not a container that wiithon can read
        NotImplementedError: If the output format is not supported
    """
    if isinstance(output, IsoOutput):
        _rebuild_iso(source, destination)
        return

    raise NotImplementedError(f"Writing {type(output).__name__} is not implemented yet")



def _rebuild_iso(source, destination):
    """
    Rebuild the ISO from a WIA or RVZ
    Args:
        source: Path to the WIA/RVZ
        destination: Path to write

    Returns:
        InvalidFormatError: If the source is not a WIA or RVZ
    """
    with open(source, "rb") as f:
        magic = f.read(len(RVZ_MAGIC_WORD))

    if magic not in (WIA_MAGIC_WORD, RVZ_MAGIC_WORD):
        raise InvalidFormatError(f"Cannot rebuild an iso from magic: {magic!r}")

    with WiaReader(source) as reader, \
        open(destination, "wb") as writer:
        IsoRebuilder(reader).write(writer)
