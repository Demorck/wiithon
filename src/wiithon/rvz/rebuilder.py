from typing import BinaryIO

from wiithon.rvz.reader import WiaReader


class IsoRebuilder:
    """
    Rebuilds the disc image from a WIA/RVZ
    """

    def __init__(self, reader: WiaReader) -> None:
        """
        Constructor

        Args:
            reader: WIA/RVZ opened
        """
        #: The WIA/RVZ Reader
        self.reader = reader

    def write_raw_data(self, stream: BinaryIO) -> None:
        """
        Wrtie every data of the disc that lives outside a partition

        Args:
            stream: Where to write (opened for writing/seeking)
        """
        chunk = self.reader.disc.chunk_size
        stream.truncate(self.reader.header.iso_file_size)

        for entry in self.reader.raw_data:
            for i in range(entry.group_count):
                group_index = entry.first_group_index + i
                if self.reader.groups[group_index].is_zero:
                    continue

                stream.seek(entry.offset + i * chunk)
                stream.write(self.reader.read_group(group_index))