============
Introduction
============

Wiithon is a Python library for reading, writing and patching Wii ISO disc images.

The library provides a high-level API to inspect and modify Wii game disc images without extracting them like:

* Adding, removing, replacing and listing files in ISO
* Extracting an ISO
* Building an ISO from directory
* Patching an ISO by patching DOL and banner
* Modifying files in U8, Yaz0 or RARC archive

Requirements
------------

* Python 3.11+
* pycryptodome 3.0+

Installing
----------

.. code-block:: bash

   pip install wiithon

Examples
--------

.. code-block:: python

   from wiithon import WiiIsoPatcher

   with WiiIsoPatcher("path/to/iso") as patcher:
       patcher.modify_title("My super romhack")
       patcher.add_file("ObjectData/NewFile.arc", file_data)

       patcher.build("game_patched.iso")