=================
Patching a Wii ISO
=================

``WiiIsoPatcher`` lets you modify a Wii ISO and rebuild it.
All modifications are collected first, then applied when ``build()`` is called.

.. code-block:: python

    from wiithon import WiiIsoPatcher

    with WiiIsoPatcher("path/to/iso") as patcher:
        # apply modifications...
        patcher.build("destination/path.iso")


File operations
---------------

..  code-block:: python

    # Replace an existing file
    patcher.replace_file("opening.bnr", new_data)

    # Add a new file
    patcher.add_file("new/path/file.arc", data)

    # Remove a file
    patcher.remove_file("path/to/file.arc")

Modifying the disc header
-------------------------

..  code-block:: python

    patcher.modify_title("My Modded Game")
    patcher.modify_title_id("RМCP99")
    patcher.modify_banner_title("My Modded Game", language="en")


Patching the DOL
----------------

The DOL is the main game executable. You can patch it by providing a callback
that receives the parsed ``DOL`` object.

..  code-block:: python

    from wiithon.file_helper.dol import DOL

    def my_patch(dol: DOL):
       dol.write_u32(0x80123456, 0xDEADBEEF)

    patcher.patch_dol(my_patch)

Adding code to the DOL
----------------------

The DOL are divided in different section. You could add one section and added to the DOL but unfortunately,
the Wii compiler hardcoded where the heap starts. So, everything you will write will be set to 0.
Wiithon support that. Since wiithon will inject the code, the ram adresses will be shifted by a certain amount.


..  code-block:: python

    from wiithon.file_helper.dol import DOL
    from wiithon.helpers import PowerPC as ppc

    def my_patch(dol: DOL):
        code = ppc.nop() * 5
        diff, addr = dol.inject_above_arena([code])

        print(f"diff in the ram @ {diff:#010x}")
        print(f"new code @ {addr[0]:#010x}")

    patcher.patch_dol(my_patch)


Working with nested archives (RARC, Yaz0)
-----------------------------------------

Many Wii game files are RARC archives, sometimes compressed with Yaz0.