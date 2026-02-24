import unittest
from io import BytesIO
from helpers.IOWindow import IOWindow


class TestIOWindow(unittest.TestCase):
    """Unit tests for IOWindow."""

    def test_read_basic(self) -> None:
        """Test basic read at different positions."""
        data = bytes(range(20))  # [0, 1, 2, ..., 19]
        source = BytesIO(data)
        win = IOWindow(source, start=5, length=10)

        result = win.read(3)
        self.assertEqual(result, bytes([5, 6, 7]))
        self.assertEqual(win.tell(), 3)

    def test_read_past_length(self) -> None:
        """Test that read is clamped to window length."""
        data = bytes(range(20))
        source = BytesIO(data)
        win = IOWindow(source, start=10, length=3)

        result = win.read(100)  # Try to read 100 bytes but the window size is 3
        self.assertEqual(result, bytes([10, 11, 12]))
        self.assertEqual(win.tell(), 3)

    def test_seek_and_read(self) -> None:
        """Test seeking then reading."""
        data = bytes(range(20))
        source = BytesIO(data)
        win = IOWindow(source, start=0, length=None)

        win.seek(5)
        result = win.read(3)
        self.assertEqual(result, bytes([5, 6, 7]))

    def test_seek_from_end(self) -> None:
        """Test seeking from end of window."""
        data = bytes(range(20))
        source = BytesIO(data)
        win = IOWindow(source, start=10, length=5)

        pos = win.seek(-2, 2)  # 2 bytes before the end
        self.assertEqual(pos, 3)
        result = win.read(2)
        self.assertEqual(result, bytes([13, 14]))

    def test_write(self) -> None:
        """Test writing data through the window."""
        data = bytearray(20)
        source = BytesIO(data)
        win = IOWindow(source, start=5)

        win.write(bytes([0xAA, 0xBB, 0xCC]))
        source.seek(5)
        self.assertEqual(source.read(3), bytes([0xAA, 0xBB, 0xCC]))

if __name__ == "__main__":
    unittest.main()