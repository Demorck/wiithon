from helpers.Utils import *


class TicketTimeLimit:
    """
    Time limit entry in a Wii Ticket (v0)

    The Ticket contains 8 consectuvive TicketTimeLimit entries that can
    restrict content usage

    References:
        https://wiibrew.org/wiki/Ticket

    Attributes:
        enable_time_limit   : `int` - Limit type (0=disabled, 1=time in minutes, 3=disabled, 4=launch count limit)
        time_limit          : `int` - Maximum value depending on type
    """
    def __init__(self) -> None:
        self.enable_time_limit: int = 0
        self.time_limit: int = 0

    @classmethod
    def read(cls, stream: BinaryIO) -> "TicketTimeLimit":
        """
        Read the time limit entry from a binary Stream.

        :param stream: Binary IO stream
        :return: Time limit entry
        """
        obj = cls()
        obj.enable_time_limit = read_u32(stream)
        obj.time_limit = read_u32(stream)

        return obj

    def write(self, stream: BinaryIO) -> None:
        """
        Write the time limit entry to a binary stream.

        :param stream: Binary IO stream
        :return: None
        """
        stream.write(struct.pack('>II', self.enable_time_limit, self.time_limit))