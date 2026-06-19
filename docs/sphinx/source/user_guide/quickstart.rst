==========
Quickstart
==========

Reading a Wii ISO
-----------------
Minimal example: Open an ISO, read the header and list all files in it.

..  code-block:: python

    from wiithon import WiiIsoReader

    with WiiIsoReader("path/to/iso") as reader:
       info = reader.disc_header
       print(info.game_id)
       print(info.game_title)

        data_partition = reader.get_data_partition()
        partition = reader.open_partition(data_partition)
        for f in partition.list_files():
           print(f)

More information :doc:`on the dedicated page for reading an ISO <reading>`

Patching a Wii ISO
------------------
Replacing a file and rebuilding the ISO

..  code-block:: python

    from wiithon import WiiIsoPatcher

    with WiiIsoPatcher("path/to/iso") as patcher:
       with open("new_file.arc", "rb") as f:
           patcher.replace_file("path/to/file.arc", f.read())
       patcher.build("dest/output.iso")

More information :doc:`on the dedicated page for patching an ISO <reading>`