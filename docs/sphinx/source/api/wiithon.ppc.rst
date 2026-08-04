===========
wiithon.ppc
===========

PowerPC instruction encoding.

The Wii runs a PowerPC 750CL. This package assembles single instructions into the
four-byte words expected by the console, which is what you need when injecting
code into a DOL.

..  toctree::
    :maxdepth: 1

    wiithon.ppc.instructions

..  rubric:: Modules

:doc:`wiithon.ppc.instructions`
    One function per instruction, returning its encoded form as ``bytes``.

..  seealso::

    :doc:`/internal/powerpc` documents the instruction formats and their bit
    fields. :doc:`/user_guide/patching` shows how to inject the result into a
    game.