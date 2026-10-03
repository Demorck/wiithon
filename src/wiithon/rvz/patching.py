from wiithon.crypto.layout import BLOCK_HEADER_SIZE, SHA1_SIZE


def hash_exceptions(stored: bytes, recomputed: bytes) -> list[tuple[int, bytes]]:
    """
    List what a reader would have to patch to turn one header into one another header

    Args:
        stored: The decrypted 0x400 header
        recomputed: The same header as hashng the data produces it

    Returns:
        One pair of offset and value per exception (ascending order)
    """
    found = []
    position = 0

    while position < BLOCK_HEADER_SIZE:
        if stored[position] == recomputed[position]:
            position += 1
            continue

        # Not the same byte
        offset = min(position, BLOCK_HEADER_SIZE - SHA1_SIZE)
        found.append((offset, stored[offset: offset + SHA1_SIZE]))
        position = offset + SHA1_SIZE

    return found