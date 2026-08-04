==============
wiithon.binary
==============

Primitives for reading and writing binary data.

Wii discs are big endian, so :class:`~wiithon.binary.reader.BinaryReader` and
:class:`~wiithon.binary.writer.BinaryWriter` default to big endian, with explicit
little endian variants where a format needs them.

..  toctree::
    :maxdepth: 1

    wiithon.binary.reader
    wiithon.binary.writer
    wiithon.binary.align
    wiithon.binary.common

..  rubric:: Modules

:doc:`wiithon.binary.reader`
    Typed reads over a stream: integers, floats, strings, raw blocks.

:doc:`wiithon.binary.writer`
    The writing counterpart, with padding and fixed-size strings.

:doc:`wiithon.binary.align`
    Rounding an offset up to a boundary.

:doc:`wiithon.binary.common`
    Shared defaults, such as the string encoding.

..  note::

    ``u32_shifted`` reads and writes the offsets that Wii discs store
    right-shifted by two bits. See :doc:`/internal/iso`.