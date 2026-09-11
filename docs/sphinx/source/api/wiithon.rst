=======
wiithon
=======

..  automodule:: wiithon

..  toctree::
    :maxdepth: 1

    wiithon.disc
    wiithon.builder
    wiithon.formats
    wiithon.fst
    wiithon.binary
    wiithon.crypto
    wiithon.ppc
    wiithon.exceptions

..  rubric:: Packages

:doc:`wiithon.disc`
    Reading and patching a disc image. This is where you start.

:doc:`wiithon.builder`
    Assembling a new ISO from partitions.

:doc:`wiithon.formats`
    Nintendo file formats: RARC, U8, Yaz0, DOL, BCSV, BNR.

:doc:`wiithon.fst`
    The file system table of a partition.

:doc:`wiithon.binary`
    Endian-aware primitives for reading and writing binary data.

:doc:`wiithon.crypto`
    AES decryption and the hash tree of partition data.

:doc:`wiithon.ppc`
    PowerPC instruction encoding, for code injection.

:doc:`wiithon.exceptions`
    Every exception the library raises.

..  note::

    The names listed in the package docstring above are re-exported for
    convenience. ``from wiithon import Rarc`` and
    ``from wiithon.formats.rarc import Rarc`` are equivalent.