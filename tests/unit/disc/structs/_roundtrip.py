from io import BytesIO


class RoundTripMixin:
    """Checks that read() and write() are mutual inverses."""

    def assert_round_trip(self, cls, raw: bytes) -> None:
        """write(read(write(read(raw)))) == write(read(raw))"""
        first = BytesIO()
        cls.read(BytesIO(raw)).write(first)

        second = BytesIO()
        cls.read(BytesIO(first.getvalue())).write(second)

        self.assertEqual(first.getvalue(), second.getvalue())