"""
Rounding helper for the offsets of a disc image

Wii structures are stored on boundaries, a file starts on 0x8000 and a section on 0x20, so almost every offset
computed by :mod:`wiithon.builder.disc_builder` goes through :func:`align`

Some files structures are also aligned like U8
"""

def align(value: int, boundary: int) -> int:
    """
    Round a value up to the next multiple of boudary

    A value that is already a multiple is returned unchanged

    Args:
        value: The number to round up
        boundary: The boundary to align on. It must be a power of 2

    Returns:
        The smallest multiple of ``boundary`` that is greater or equal to ``value``

    Warning:
        The boundary is not checked. If the boundary is not a power of two, the result will be wrong

    Examples:
        >>> align(0x1234, 0x20)
        4672 # = 0x1240
        >>> align(0x400, 0x20)
        1024 # = 0x400
    """
    return (value + boundary - 1) & ~(boundary - 1)