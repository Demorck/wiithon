"""
PRNG used in padding for Gamecube and Wii disc.

A lagged Fibonacci Generator with ``f = XOR``, ``j = 32`` and ``k = 521``.

See Also:
    * `Wikipedia: Lagged Fibonacci Generator <https://en.wikipedia.org/wiki/Lagged_Fibonacci_generator>`_
    * `Dolphin: WIA and RVZ docs <https://github.com/dolphin-emu/dolphin/blob/master/docs/WiaAndRvz.md>`_
"""
import struct

K: int = 521
J: int = 32

SEED_WORDS: int = 17
SEED_SIZE:  int = SEED_WORDS * 4

BUFFER_SIZE: int = K * 4

class LaggedFibonacci:
    """
    Implementation of the Lagged Fibonacci Generator used for padding in Gamecube and wii games
    """

    def __init__(self, seed: bytes) -> None:
        """
        Args:
            seed: 68 bytes big endian seed, stored in an RVZ group

        Raises:
            ValueError: If seed is not exactly 68 bytes long
        """
        if len(seed) != SEED_SIZE:
            raise ValueError(f"Seed must be {SEED_SIZE} bytes long, got {len(seed)}")

        words = list(struct.unpack(f">{SEED_WORDS}I", seed)) + [0] * (K - SEED_WORDS)


        for i in range(SEED_WORDS, K):
            words[i] = (
                (words[i - 17] << 23) ^
                (words[i - 16] >> 9) ^
                (words[i - 1])
            ) & 0xFFFFFFFF

        self._words: list[int] = [
            (w & 0xFF00FFFF) |
            ((w >> 2) & 0x00FF0000) for w in words
        ]

        #: Byte version of the current state
        self._block: bytes = b''

        #: Position in _block in bytes
        self._position: int = 0

        # Warmup / Initial round
        for _ in range(4):
            self._advance()

    def _advance(self) -> None:
        """Step the state by one full buffer"""
        for i in range(J):
            self._words[i] ^= self._words[i + K - J]

        for i in range(J, K):
            self._words[i] ^= self._words[i - J]

        self._block = struct.pack(f">{K}I", *self._words)

    def skip(self, count: int) -> None:
        """
        Discard the next ``count`` bytes.

        Args:
            count: Number of bytes to skip

        Raises:
            ValueError: If ``count`` is strictly negative
        """

        if count < 0:
            raise ValueError(f"Cannot skip a negative number of bytes. Count must be >= 0, got {count}")

        self._position += count
        while self._position >= BUFFER_SIZE:
            self._advance()
            self._position -= BUFFER_SIZE

    def read(self, count: int) -> bytes:
        """
        Produce ``count`` bytes from the buffer.

        Args:
            count: Number of bytes to read

        Raises:
            ValueError: If ``count`` is strictly negative
        """
        if count < 0:
            raise ValueError(f"Cannot read a negative number of bytes. Count must be >= 0, got {count}")

        out = bytearray()
        while count > 0:
            chunk = min(count, BUFFER_SIZE - self._position)

            out += self._block[self._position:self._position + chunk]
            self._position += chunk
            count -= chunk

            if self._position == BUFFER_SIZE:
                self._advance()
                self._position = 0


        return bytes(out)