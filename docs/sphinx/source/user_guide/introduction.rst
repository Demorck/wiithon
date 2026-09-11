============
Introduction
============

Wiithon is a Python library for reading, writing and patching Wii ISO disc images.

It provides a high-level API to inspect and modify a disc image **in place**, without
extracting it to disk first:

* List, read, add, replace and remove files inside an ISO
* Extract a full ISO to a directory
* Build an ISO back from a directory
* Patch the DOL executable and the banner
* Read and write files nested in U8, RARC and Yaz0 archives

..  note::

    Wiithon does not ship any game data. You need to provide your own disc image,
    dumped from a disc you own.

Requirements
------------

* Python 3.11 or newer
* `pycryptodome <https://pypi.org/project/pycryptodome/>`_ 3.0+ - AES decryption of partitions
* `typer <https://typer.tiangolo.com/>`_ and `rich <https://rich.readthedocs.io/>`_ - command line interface

Installing
----------

..  code-block:: bash

    pip install wiithon

Or from a clone, in editable mode:

..  code-block:: bash

    git clone https://github.com/Demorck/wiithon
    cd wiithon
    pip install -e .

A first look
------------

..  code-block:: python

    from wiithon import WiiIsoPatcher

    with WiiIsoPatcher("game.iso") as patcher:
        patcher.modify_title("My super romhack")
        patcher.add_file("ObjectData/NewFile.arc", file_data)

        patcher.build("game_patched.iso")

..  important::

    Wiithon never writes to the source ISO. Every modification is buffered and
    only materialised in the file passed to ``build()``.

Where to go next
----------------

..  seealso::

    :doc:`quickstart`
        The shortest path to reading and patching an ISO.

    :doc:`reading`
        Inspecting a disc without modifying it.

    :doc:`patching`
        Modifying files, the disc header and the DOL.

    :doc:`/internal/iso`
        How a Wii disc is actually laid out, if you want to know *why*.