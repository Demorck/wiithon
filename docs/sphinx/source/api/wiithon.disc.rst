============
wiithon.disc
============

Reading and patching a Wii disc image, and the structures a disc is made of.

Start with :class:`~wiithon.disc.reader.WiiIsoReader` to inspect a disc, or
:class:`~wiithon.disc.patcher.WiiIsoPatcher` to modify one.

..  toctree::
    :maxdepth: 1

    wiithon.disc.reader
    wiithon.disc.patcher
    wiithon.disc.partition
    wiithon.disc.enums
    wiithon.disc.layout
    wiithon.disc.structs

..  rubric:: Modules

:doc:`wiithon.disc.reader`
    Read-only access to an ISO. Parses the disc header and the partition table.

:doc:`wiithon.disc.patcher`
    Collects modifications and rebuilds an ISO.

:doc:`wiithon.disc.partition`
    Contents of a decrypted partition: files, DOL, apploader.

:doc:`wiithon.disc.enums`
    Partition types.

:doc:`wiithon.disc.layout`
    Fixed offsets and sizes of the disc format.

:doc:`wiithon.disc.structs`
    On-disc structures: header, ticket, TMD, certificates.

..  seealso::

    :doc:`/internal/iso` explains what these structures mean and where they sit
    on the disc.