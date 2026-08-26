=========================
PowerPC for patching
=========================

The Wii runs a PowerPC 750CL, nicknamed Broadway. It is 32-bit, big endian and every instruction is exactly
four bytes. That last property is what makes binary patching practical: you can always overwrite one
instruction with another without moving anything.

You could do that by manually changing some nop instructions (`0x60000000`) by an another one like: (`0x38600045`).
Do you know what is it ? Maybe but it's unreadable. Wiithon has a PowerPC module for that !

:mod:`wiithon.ppc.instructions` assembles single instructions. Each function returns four bytes.

..  code-block:: python

    from wiithon.ppc import instructions as ppc

    ppc.nop()          # b'\\x60\\x00\\x00\\x00'
    ppc.li(3, 69)      # load 69 into r3
    ppc.blr()          # return to caller

Registers
=========

There are 32 general purpose registers, ``r0`` to ``r31``. The ones you will meet constantly:

==========  ==================================================================
Register    Role
==========  ==================================================================
``r0``      Scratch. Reads as literal zero in some addressing forms
``r1``      Stack pointer. Do not clobber it
``r2``      Pointer to the read-only small data area
``r3``      First argument and the return value
``r4-r10``  Further arguments
``r13``     Pointer to the read-write small data area
==========  ==================================================================

If you remember one line of this table, make it ``r3``. It carries the first argument on the way in and the
return value on the way out, which is why almost every patch you will ever write touches it

Two special registers matter for patching. ``LR`` holds the return address and ``CTR`` is used for indirect
calls. ``ppc.mflr`` and ``ppc.mtlr`` move values in and out of ``LR``.

32-bit constant
===============

An instruction is four bytes, so it cannot carry a 32-bit immediate. Loading a full address always takes two
instructions: one for the top half, one for the bottom.

..  code-block:: python

    code = ppc.lis(3, 0x8069) + ppc.ori(3, 3, 0xCCA0)   # r3 = 0x8069CCA0

..  important::

    Use ``ori``, not ``addi``, unless you know what you are doing. ``addi`` **sign-extends** its immediate, so
    a low half of ``0x8000`` or more is treated as negative and you lose ``0x10000`` from the result. To use
    ``addi`` you must compensate by incrementing the high half.

That is not a theoretical concern. It is exactly why :meth:`~wiithon.formats.dol.DOL.patch_arena_lo` emits an
``ori`` and why :meth:`~wiithon.formats.dol.DOL.read_arena_lo` checks the opcode before decoding::

    lo = (lo_raw - 0x10000) if ((w1 >> 26) == 14 and lo_raw >= 0x8000) else lo_raw

Opcode 14 is ``addi``. When the original game used one, the low half has to be read back as signed.

Written by hand, loading ``0x8069CCA0`` means emitting ``3C608069`` then ``6063CCA0`` and remembering that
the second word would have to be ``60630000 | 0xCCA0``. Now do it for an address ending in ``0x8004``, with
``addi`` this time. That is the kind of arithmetic you get wrong once, at two in the morning and spend an
evening tracking down.

Branches are relative
=====================

A branch encodes a **displacement**, not a destination. The assembler therefore needs to know where the
instruction will live:

..  code-block:: python

    ppc.b(target=0x80600000, from_addr=0x80123456)    # jump
    ppc.bl(target=0x80600000, from_addr=0x80123456)   # call, sets LR

Getting ``from_addr`` wrong produces a branch that lands somewhere else entirely and the game will crash far
from the actual mistake.

``ba`` and ``bla`` take an absolute target instead, but the encoding only carries 26 bits, so they can only
reach the low addresses. They are rarely what you want on Wii.

Common patches
==============

**Neutralise a call.** The single most useful patch and the safest, since the surrounding code keeps its
layout:

..  code-block:: python

    dol.write_at(0x80123456, ppc.nop())

**Force a return value.** Make a check always succeed:

..  code-block:: python

    dol.write_at(0x80123456, ppc.li(3, 1) + ppc.blr()) # true = 1

**Change a constant.** Find the ``li`` that sets a lives counter and rewrite it:

..  code-block:: python

    dol.write_at(0x80123456, ppc.li(3, 99))

**Hook a function.** Replace one instruction with a call to your own code and have your code end with
``blr``:

..  code-block:: python

    HOOK = 0x80123456

    def patch(dol):
        my_code = ppc.li(3, 42) + ppc.blr()
        _, (addr,) = dol.inject_above_arena([my_code])
        dol.write_at(HOOK, ppc.bl(addr, HOOK))

..  warning::

    ``bl`` overwrites ``LR``. If the instruction you replaced was inside a function that has not saved ``LR``
    yet, or if your code returns before restoring it, the game will return to the wrong address. Save and
    restore it with ``mflr`` and ``mtlr`` when in doubt.

Available instructions
======================

The module covers what binary patching normally needs:

* branches: ``b``, ``bl``, ``ba``, ``bla``, ``bc``, ``bcl``, ``bclr``, ``bclrl``, ``blr``, ``blrl``
* immediates: ``li``, ``lis``, ``addi``, ``addis``, ``mulli``, ``ori``, ``oris``, ``andi``
* memory: ``lwz``, ``stw``, ``lhz``, ``sth``, ``lbz``, ``stb``, ``lfs``, ``stfs``
* memory with update: ``lwzu``, ``stwu``, ``lhzu``, ``sthu``, ``lbzu``, ``stbu``
* memory, indexed: ``lbzx``
* arithmetic and logic: ``add``, ``subf``, ``and_``, ``or_``, ``mr``, ``cntlzw``, ``rlwnm``
* comparison: ``cmp``, ``cmpi``
* special registers: ``mfspr``, ``mtspr``, ``mflr``, ``mtlr``, ``mfctr``, ``mtctr``
* ``nop``

Arguments are validated. Passing a register number above 31 or an immediate that does not fit raises rather
than silently truncating.

The update forms write the computed address back into ``rA``, which makes walking a structure a single
instruction per step instead of two. The hardware forbids ``rA`` being ``r0`` and forbids ``rA`` and ``rD``
being the same register. Wiithon raises rather than emitting an instruction the CPU treats as invalid.

If you think you need something that it's not here, feel free to open an issue on github.

..  seealso::

    :doc:`/internal/powerpc` documents the instruction formats and their bit fields, if you need to encode
    something the module does not provide.