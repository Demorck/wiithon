===================
Reading a Wii ISO
===================

``WiiIsoReader`` is the entry point for inspecting a Wii ISO without modifying it.
Always use it as a context manager to ensure the file is properly closed.

.. code-block:: python

   from wiithon import WiiIsoReader

   with WiiIsoReader("path/to/iso") as reader:
       ...


Disc information
----------------

.. code-block:: python

   with WiiIsoReader("path/to/iso") as reader:
       header = reader.disc_header
       print(header.game_id)      # b'RMCP01'
       print(header.game_title)   # 'Mario Kart Wii'
       print(header.disc_num)
       print(header.disc_version)


Partitions
----------

A Wii disc contains one or more partitions. Most games have a data partition
and an update partition. Some games have channel partitions (like Mario Kart Wii).
Channel partition is **not** currently supported.

.. code-block:: python

   with WiiIsoReader("path/to/iso") as reader:
       data    = reader.get_data_partition()
       update  = reader.get_update_partition()
       all     = reader.get_partitions()


Opening a partition
-------------------

To access files inside a partition, you need to open it first.
This decrypts the partition header and loads the FST.

.. code-block:: python

   with WiiIsoReader("path/to/iso") as reader:
       partition = reader.open_partition(reader.get_data_partition())


Listing and reading files
-------------------------

.. code-block:: python

   with WiiIsoReader("path/to/iso") as reader:
       partition = reader.open_partition(reader.get_data_partition())

       for path in partition.list_files():
           print(path)

       data = partition.read_file("opening.bnr")


Reading the DOL
---------------

The main executable of the game is stored as a DOL file.

.. code-block:: python

   with WiiIsoReader("path/to/iso") as reader:
       partition = reader.open_partition(reader.get_data_partition())
       dol = partition.read_dol()
