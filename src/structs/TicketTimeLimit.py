from Utils import *

class TicketTimeLimit:
    """
    Time limit entri in a Wii Ticket.
    Found in the v0 ticket here: https://wiibrew.org/wiki/Ticket
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