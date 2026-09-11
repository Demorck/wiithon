"""
Settings shared by the reader and the writer

This module holds only the default encoding, so importing it does not pull the whole :mod:`wiithon.binary`
package in
"""

#: Default encoding of :class:`~wiithon.binary.reader.BinaryReader` and
#: :class:`~wiithon.binary.writer.BinaryWriter`. Formats that store japanese text, like BCSV or RARC, pass
#: ``shift_jis`` per call or in the constructor instead of changing this
STRING_FORMAT: str = "utf-8"