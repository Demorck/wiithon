=================
Reading a Wii ISO
=================

:class:`~wiithon.disc.reader.WiiIsoReader` is the entry point for inspecting a Wii
ISO without modifying it.

..  code-block:: python

    from wiithon import WiiIsoReader

    with WiiIsoReader("game.iso") as reader:
        ...

..  tip::

    Always use it as a context manager. It holds an open file handle, and the
    ``with`` block guarantees it gets closed even if something raises.

Disc information
----------------

The unencrypted disc header sits at offset ``0x000`` and is read as soon as the
ISO is opened.

..  code-block:: python

    with WiiIsoReader("game.iso") as reader:
        header = reader.disc_header

        print(header.game_id)        # b'RMGE01'
        print(header.game_title)     # 'SUPER MARIO GALAXY'
        print(header.disc_num)       # 0
        print(header.disc_version)   # 0

..  note::

    ``game_id`` is raw ``bytes``, not ``str``. It is copied verbatim from the disc.
    ``game_title`` is decoded for you.

..  seealso::

    :doc:`/internal/iso` describes every field of the disc header and its offset.

Partitions
----------

A Wii disc holds one or more partitions. Most games have a ``DATA`` partition
containing the game itself, and an ``UPDATE`` partition holding a system update.

..  code-block:: python

    with WiiIsoReader("game.iso") as reader:
        data   = reader.get_data_partition()
        update = reader.get_update_partition()
        every  = reader.get_partitions()

..  warning::

    ``get_data_partition()`` and ``get_update_partition()`` return ``None`` when the
    partition is absent an update partition is optional. Check the result before
    passing it on.

..  warning::

    ``CHANNEL`` partitions are **not supported yet**. Games that ship virtual
    channels, like Super Smash Bros. Brawl, expose them through
    ``get_partitions()`` but they cannot be opened.

Opening a partition
-------------------

Opening a partition decrypts its header, reads the ticket and TMD, and loads the
file system table.

..  code-block:: python

    with WiiIsoReader("game.iso") as reader:
        partition = reader.open_partition(reader.get_data_partition())

The result is a :class:`~wiithon.disc.partition.WiiPartitionInfo`, which is what
you use for everything file-related.

Listing and reading files
-------------------------

..  code-block:: python

    with WiiIsoReader("game.iso") as reader:
        partition = reader.open_partition(reader.get_data_partition())

        for path in partition.list_files():
            print(path)

        print(f"{len(partition.list_files())} files")

        data = partition.read_file("opening.bnr")

For a large disc, ``list_files()`` builds the whole list in memory. To walk the
tree without materialising it, use a callback:

..  code-block:: python

    def show(node):
        print(node.name)

    partition.callback_all_files(show)

System files
------------

Some files live outside the file system table and have dedicated accessors.

..  code-block:: python

    dol       = partition.read_dol()          # main executable, parsed as DOL
    apploader = partition.read_apploader()    # raw bytes
    bi2       = partition.read_bi2()          # raw bytes

..  seealso::

    :doc:`patching` to modify what you just read, and :doc:`file_formats` to parse
    the files you extracted.