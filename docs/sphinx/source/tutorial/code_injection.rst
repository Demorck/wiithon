==============
Code injection
==============

Adding a few instructions is easy. Adding a *routine* is not, and the reason has nothing to do with the DOL
format.

Why you cannot just append a section
====================================

A Wii game does not own the whole of MEM1. Its static data ends somewhere, and everything above that point is
the heap, which the game calls the arena. The lower bound of the arena is a value named **arenaLo**.

If you declare a new section above the game's data, you are declaring it inside the heap. The game will
allocate over your code within the first seconds of running, and your code will be replaced by a bunch of zeroes (or
maybe a crash, sometimes)

..  warning::

    ``bss_start + bss_size`` is not arenaLo. Across every game measured, arenaLo sits roughly ``0x10000``
    higher. Computing an injection address from ``bss`` gives you an address that is free at load time and
    allocated shortly after.

The fix is to move arenaLo up, so the heap starts above your code instead of on top of it. The game loses that
much memory, and everything else keeps working.

You are probably wondering: "Why can't I put my code between the end of bss and arenaLo ?". And the question is
completely correct. There is a bunch of static data, maybe written by the compiler for fast access. In Super Mario
Galaxy, Mario Object pointer is written in ``0x806B7B40``, between ``bss_end`` and start of ``arenaLo``.


Finding arenaLo
===============

arenaLo is not stored in a table. It is a constant compiled into the boot code, loaded into ``r3`` and passed
to the function that initialises the heap. The sequence is remarkably stable across games:

..  code-block:: asm

    lis    r3, HI      ; 3c 60 ?? ??   <- the instruction to patch
    addi   r3, r3, LO  ; 38 63 ?? ??
    addi   r0, r3, 31  ; 38 03 ?? ??
    rlwinm r3, r0, ?   ; 54 03 ?? ??

The last two instructions round the value up to a 32-byte boundary, which is what makes the pattern
recognisable: a bare ``lis``/``addi`` pair is everywhere, but one immediately followed by an align-to-32 is not.

..  code-block:: python

    site = dol.find_arena_lo_setter()
    print(f"setter at {site:#010x}, arenaLo = {dol.read_arena_lo(site):#010x}")

The scan walks every text section four bytes at a time and returns the address of the ``lis``. If no match is
found it raises :class:`~wiithon.exceptions.DolError`.

Known values
------------

If the scan fails, or if you want to check its result, these were measured by hand:

===================  ========  ==============  =====================  ==============
Game                 ID        arenaLo         arenaLo minus bss_end  Setter address
===================  ========  ==============  =====================  ==============
Skyward Sword        SOUE01    ``0x806882C0``  ``+0x10000``           ``0x803A2AF0``
Super Mario Galaxy   RMGE01    ``0x806BDFA0``  ``+0x10010``           ``0x804A16BC``
Mario Strikers       RSBE01    ``0x806F6D20``  ``+0x1001C``           ``0x803B1F74``
Mario Kart Wii       RMCE01    ``0x80394E00``  ``+0x10004``           ``0x8019FD28``
Wii Sports (Rev1)    RSPE01    ``0x804D6A20``  ``+0x10004``           ``0x800EC978``
Wii Sports (Rev0)    RSPE01    ``0x804F6D80``  ``+0x1000C``           ``0x800C65B4``
===================  ========  ==============  =====================  ==============

..  note::

    If you find a game where this pattern matches something that is not the arenaLo or arenaHi setter, please
    open an issue. The pattern has held on every title tested so far.

Injecting
=========

:meth:`~wiithon.formats.dol.DOL.inject_above_arena` does the whole dance: it finds the setter, reads the
current arenaLo, places your sections above it, and rewrites the setter to point past them.

..  code-block:: python

    from wiithon import DOL, WiiIsoPatcher
    from wiithon.ppc import instructions as ppc

    def patch(dol: DOL) -> None:
        routine = ppc.li(3, 42) + ppc.blr()

        shift, addresses = dol.inject_above_arena([routine])

        print(f"arena moved up by {shift:#x} bytes")
        print(f"routine lives at {addresses[0]:#010x}")

    with WiiIsoPatcher("game.iso") as patcher:
        patcher.patch_dol(patch)
        patcher.build("patched.iso")

Each section is placed on a 32-byte boundary. ``padding_before`` leaves a gap between the old arenaLo and your
first section, ``0x100`` bytes by default, which gives you room to grow without changing every address.

.. tip::

    ``inject_above_arena`` returns 2 arguments. The first one is the shift amount in the RAM. If something was in
    ``0x80481516`` in the RAM and the shift is ``0x200``, so the value will be at: ``0x80481716``. You can reserve a fix
    region to always have the same shift. See below.

Reserving a fixed region
------------------------

By default arenaLo is moved to just past your code, so **every time your code changes size, every address
moves**. That makes iteration painful, and it invalidates any address you hardcoded elsewhere.

``reserved_size`` fixes the layout:

..  code-block:: python

    shift, addresses = dol.inject_above_arena([routine], reserved_size=0x4000)

arenaLo now always lands at ``base + 0x4000``, whatever your code weighs. Grow your routine and the addresses
stay put. Exceed the reservation and you get a ``ValueError`` telling you how much you used, instead of a
silent corruption.

..  tip::

    Reserve from the first day. Recompiling and discovering every address shifted by ``0x20`` is the most
    common source of wasted time in this workflow.

When the scan fails
-------------------

Pass the setter address yourself:

..  code-block:: python

    shift, addresses = dol.inject_above_arena([routine], manual_arena=0x804A16BC)

Limits
======

**Section slots.** A DOL holds 7 text and 11 data sections. ``inject_above_arena`` takes a free text slot if
there is one, falls back to a data slot, and raises
:class:`~wiithon.exceptions.DolNoFreeSectionError` when both are exhausted. Most retail games use 2 text and 8
to 9 data sections, so you have room, but not unlimited room. Concatenate your code into fewer sections rather
than adding one per function.

**Memory.** Whatever you take from the arena, the game no longer has. A few kilobytes is invisible. A few
megabytes will make a game that allocates near its limit fail in ways that look unrelated to your patch.

..  seealso::

    :doc:`ppc` for writing the code you are about to inject, and :doc:`dol` for code caves, which are the
    better option below a hundred bytes or so.