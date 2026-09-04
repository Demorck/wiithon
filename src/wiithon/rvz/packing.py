"""
The RVZ packing scheme which stores runs of disc padding as a 68 bytes seed instead of the bytes themself
"""
from wiithon.crypto.layout import BLOCK_SIZE
from wiithon.rvz.layout import PACKED_PRNG_FLAG, PACKED_SIZE_MASK
from wiithon.rvz.lfg import LaggedFibonacci, SEED_SIZE


def unpack(data: bytes, offset: int) -> bytes:
    """
    Decode a packed stream back into the bytes it stands for

    The data is a sequence of token. First bit is to say: "it's generated or not" and the rest of data is the data
    to copy or the PRNG seed

    Args:
        data: The packed stream, decompressed
        offset: Where the output starts.

    Returns:
        The decoded bytes
    """
    out = bytearray()
    position = 0

    while position < len(data):
        size = int.from_bytes(data[position:position + 4])
        position += 4

        if not size & PACKED_PRNG_FLAG:
            out += data[position:position + size]
            position += size
            continue

        generator = LaggedFibonacci(data[position:position + SEED_SIZE])
        position += SEED_SIZE

        generator.skip((offset + len(out)) % BLOCK_SIZE)
        out += generator.read(size & PACKED_SIZE_MASK)

    return bytes(out)