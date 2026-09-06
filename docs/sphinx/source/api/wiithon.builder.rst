===============
wiithon.builder
===============

Assembling a Wii ISO, partition by partition.

:class:`~wiithon.builder.disc_builder.WiiDiscBuilder` writes the disc. It does
not know where the content comes from: each partition is described by a
:class:`~wiithon.builder.source.PartitionSource`, and two implementations ship
with the library.

..  toctree::
    :maxdepth: 1

    wiithon.builder.disc_builder
    wiithon.builder.source
    wiithon.builder.copy_source
    wiithon.builder.directory_source

..  rubric:: Modules

:doc:`wiithon.builder.disc_builder`
    Writes partitions to a stream and finalises the disc.

:doc:`wiithon.builder.source`
    The ``PartitionSource`` interface. Implement it to build a partition from
    somewhere else.

:doc:`wiithon.builder.copy_source`
    Builds a partition from an existing ISO, with optional overrides of the FST,
    the DOL and individual files. This is what ``WiiIsoPatcher`` uses.

:doc:`wiithon.builder.directory_source`
    Builds a partition from a directory tree on disk.

..  note::

    For simple edits you do not need this package.
    :class:`~wiithon.disc.patcher.WiiIsoPatcher` drives the builder for you.
    See :doc:`/user_guide/patching`.