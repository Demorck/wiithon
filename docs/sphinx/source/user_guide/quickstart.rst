==========
Quickstart
==========

Reading a Wii ISO
-----------------

Open an ISO, read its header and list every file it contains.

..  code-block:: python

    from wiithon import WiiIsoReader

    with WiiIsoReader("path/to/game.iso") as reader:
        header = reader.disc_header
        print(header.game_id)      # b'RMGE01'
        print(header.game_title)   # 'SUPER MARIO GALAXY'

        partition = reader.open_partition(reader.get_data_partition())
        for path in partition.list_files():
            print(path)

See :doc:`reading` for the full reading API.

Patching a Wii ISO
------------------

Replace a file and rebuild the ISO.

..  code-block:: python

    from wiithon import WiiIsoPatcher

    with WiiIsoPatcher("path/to/game.iso") as patcher:
        with open("new_file.arc", "rb") as f:
            patcher.replace_file("path/to/file.arc", f.read())

        patcher.build("output.iso")

See :doc:`patching` for the full patching API.