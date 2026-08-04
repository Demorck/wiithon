==============
wiithon.crypto
==============

Decryption and encryption of partition data.

Partition data is stored in blocks of ``0x8000`` bytes, each carrying a header of
hashes and its own AES initialisation vector. Reading is straightforward. Writing
is not: changing a single byte means recomputing a whole tree of SHA-1 hashes
before re-encrypting.

..  toctree::
    :maxdepth: 1

    wiithon.crypto.part_reader
    wiithon.crypto.part_writer
    wiithon.crypto.blocks
    wiithon.crypto.keys
    wiithon.crypto.layout

..  rubric:: Modules

:doc:`wiithon.crypto.part_reader`
    Random access reads into a partition, decrypting blocks on demand.

:doc:`wiithon.crypto.part_writer`
    Writes a partition, rebuilding the hash tree as it goes.

:doc:`wiithon.crypto.blocks`
    Block and group level decryption and encryption.

:doc:`wiithon.crypto.keys`
    Nintendo common keys, and title key derivation.

:doc:`wiithon.crypto.layout`
    Block, subblock and group sizes.

..  warning::

    ``COMMON_KEYS`` contains the Nintendo common keys, required to derive the
    title key of any retail disc.

..  seealso::

    :doc:`/internal/iso` describes the block layout and the hash tree, with
    sequence diagrams.