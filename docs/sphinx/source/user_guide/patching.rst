==================
Patching a Wii ISO
==================

``WiiIsoPatcher`` lets you modify a Wii ISO and rebuild it.
Modifications are collected first, then applied when ``build()`` is called.

..  code-block:: python

    from wiithon import WiiIsoPatcher

    with WiiIsoPatcher("path/to/game.iso") as patcher:
        # apply modifications...
        patcher.build("output.iso")

Nothing is written until ``build()`` runs, so the source ISO is never touched.

File operations
---------------

..  code-block:: python

    # Replace an existing file
    patcher.replace_file("opening.bnr", new_data)

    # Add a new file
    patcher.add_file("ObjectData/NewFile.arc", data)

    # Remove a file
    patcher.remove_file("ObjectData/Unused.arc")

    # Read a file without modifying it
    data = patcher.read_file("opening.bnr")

    # List every file in the data partition
    for path in patcher.list_files():
        print(path)

Modifying the disc header
-------------------------

..  code-block:: python

    patcher.modify_title("My Modded Game")
    patcher.modify_title_id("RMGE99")
    patcher.modify_banner_title("My Modded Game", language="English")

``modify_title_id`` expects exactly 6 ASCII characters and raises ``RuntimeError``
otherwise. It also rewrites the ticket title ID.

``modify_banner_title`` writes into the IMET header of ``opening.bnr``.
Accepted languages are ``Japanese``, ``English``, ``German``, ``French``,
``Spanish``, ``Italian``, ``Dutch``, ``Simplified Chinese``,
``Traditional Chinese`` and ``Korean``. Any other value raises ``ValueError``.

Patching the DOL
----------------

The DOL is the main game executable. ``patch_dol`` registers a callback that
receives the parsed :class:`~wiithon.formats.dol.DOL` object. The callback runs
during ``build()``, not immediately.

..  code-block:: python

    from wiithon import DOL

    def my_patch(dol: DOL) -> None:
        dol.write_at(0x80123456, (0xDEADBEEF).to_bytes(4, "big"))

    patcher.patch_dol(my_patch)

``patch_dol`` can be called several times. The callbacks run in the order you registered them. Each seeing the
DOL as the previous one left it which lets you keep one function per patch instead of one big one.

Extra arguments are forwarded, so a patch can be parameterised:

..  code-block:: python

    def set_lives(dol: DOL, address: int, count: int) -> None:
        dol.write_at(address, ppc.li(3, count))

    patcher.patch_dol(set_lives, 0x80123456, count=99)

``write_at`` takes a virtual address and raw bytes. To read back:

..  code-block:: python

    value = dol.read_at(0x80123456, 4)

Adding code to the DOL
----------------------

A DOL is split into sections. You can append one, but the Wii compiler hardcodes
where the heap starts, so anything written past that point gets zeroed at boot.

``inject_above_arena`` works around this by moving the heap start upwards. It
returns the shift applied to the arena and the virtual address of each injected
section.

..  code-block:: python

    from wiithon import DOL
    from wiithon.ppc import instructions as ppc

    def my_patch(dol: DOL) -> None:
        code = ppc.nop() * 5
        diff, addrs = dol.inject_above_arena([code])

        print(f"arena shifted by {diff:#010x}")
        print(f"new code at {addrs[0]:#010x}")

    patcher.patch_dol(my_patch)

See :doc:`/internal/powerpc` for the instruction encodings available in
``wiithon.ppc.instructions``.

Working with nested archives
----------------------------

Many game files are archives (RARC, U8), sometimes Yaz0-compressed, and often
contain the file you actually want to edit. ``edit_as`` handles the whole
round trip: it reads the file, parses it as the class you pass, hands you the
object, then re-serialises and writes it back when the block exits.

..  code-block:: python

    from wiithon import BCSV
    from wiithon.formats.bcsv import calculate_field_hash

    FIELD_NAMES = {
        calculate_field_hash("ScenarioNo"):     "ScenarioNo",
        calculate_field_hash("LuigiModeTimer"): "LuigiModeTimer",
    }

    path = "StageData/CannonFleetGalaxy/CannonFleetGalaxyScenario.arc/scenariodata.bcsv"

    with WiiIsoPatcher("path/to/game.iso") as patcher:
        with patcher.edit_as(path, BCSV, field_names=FIELD_NAMES, str_fmt="shift_jis") as bcsv:
            for entry in bcsv.entries:
                entry["LuigiModeTimer"] = 0

        patcher.build("output.iso")

The path crosses the archive boundary: ``...Scenario.arc/scenariodata.bcsv``
points inside the RARC archive. Extra keyword arguments are forwarded to the
class's ``read()`` method.