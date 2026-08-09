====================
Working with the DOL
====================

The DOL is the game executable. Everything the game does is here. Most non-trivial patches touch it.

Layout
======

A DOL is a header of ``0x100`` bytes followed by raw section data. There are no relocations and no symbol table.
Each section declares the virtual address it must be loaded at and the console copies it.

A DOL holds at most **7 text sections** and **11 data sections**. Unused slots have a length of zero.

.. code-block:: python

    from wiithon import WiiIsoReader

    with WiiIsoReader("path/to/iso") as reader:
        partition = reader.open_partition(reader.get_data_partition())
        dol = partition.read_dol()

        print(dol.header)

Which prints something like::

    entry:  8000403C
    bss:    805F5A40 — 806ADF90  (size: 000B8550)

    text[0]: 80004000 — 800064E0  (size: 000024E0)
    text[1]: 800070A0 — 8052D280  (size: 005261E0)
    data[0]: 800064E0 — 800069A0  (size: 000004C0)
    ...

Three things to read off that dump:

* addresses start at ``0x80000000``, which is where :term:`MEM1` is mapped. A Wii has 24 MB of MEM1, so valid code
  addresses run up to roughly ``0x81800000``
* ``text[0]`` is almost always the same small block across games. It is the init stub
* ``bss`` is declared but not stored. It is zeroed at load time, which is why it has a size but no offset

..  warning::

    ``bss_start + bss_size`` is **not** the end of the game's memory. The heap starts about 64 KB further up.
    See :doc:`code_injection` before assuming anything past ``bss`` is free.

Reading and writing
===================

You address the DOL by **virtual address**, not by file offset. Wiithon resolves which section contains the
address and translates for you.

..  code-block:: python

    value = dol.read_at(0x80123456, 4)
    dol.write_at(0x80123456, b"\x60\x00\x00\x00")

    text = dol.read_until_null_at(0x805A1234)


``write_at`` refuses to write outside any loaded section, so a typo in an address fails loudly instead of
corrupting a neighbouring section.

Finding free space
==================

Compilers leave gaps. Alignment padding, removed code and unused stubs show up as long runs of ``nop``
(``0x60000000``) or zero words. Those runs are called code caves and they are the simplest place to put a
small routine, since they need no section juggling at all.

..  code-block:: python

    for name, address, size in dol.find_code_caves(min_size=0x80):
        print(f"{name:8} {address:#010x}  {size:#x} bytes")

..  code-block:: text

    text[1]  0x801a4f60  0xc0 bytes
    text[1]  0x8021b800  0x1a0 bytes
    data[4]  0x80251340  0x100 bytes

The same scan is available from the command line::

    wiithon dol caves game.iso --min-size 128

..  warning::

    A cave being full of zeros does not prove it is unused. Zeroed data sections are common and a run of nops
    inside a text section may be a jump table the game fills at runtime. Test in an emulator before trusting one.
    Dolphin has a memory engine integrated if you run it in debug mode.

..  tip::

    Caves are fine for a few dozen instructions. Past that, add a section instead. See :doc:`code_injection`.
    It will be more readable.

Adding a section
================

When there is a free slot, you can declare a whole new section at an address of your choosing.

..  code-block:: python

    if dol.has_free_text_section():
        dol.add_text_section(0x80600000, my_code)

The address must not overlap any existing section and it must be somewhere the game will not scribble over.
That second condition is the hard one and it is the whole subject of :doc:`code_injection`.

..  seealso::

    :class:`~wiithon.formats.dol.DOL` for the complete method list and :doc:`/user_guide/patching` for wiring a
    patch into ``WiiIsoPatcher``.
