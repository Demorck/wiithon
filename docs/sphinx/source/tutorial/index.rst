========
Tutorial
========

The user guide shows you the shortest path. This section explains what is actually happening, so you can go
further than the recipes.

Each chapter stands on its own. Read the one you need.

..  toctree::
    :maxdepth: 1

    dol
    ppc
    code_injection
    files
    rebuilding

..  rubric:: Chapters

:doc:`dol`
    The game executable: how it is laid out, how to read and write memory in it, and where the free space is. Changing
    the game code is here.

:doc:`ppc`
    Enough PowerPC to write your own patches and the traps of a fixed-width instructions set

:doc:`code_injection`
    Adding new code to a game that has no room for it, and why the heap is the obstacle

:doc:`files`
    Adding, removing or modifying files

:doc:`rebuilding`
    Rebuilding the ISO and save your progress

..  note::

    These chapters assume you are comfortable with :doc:`/user_guide/patching`. They pick up where it stops
    explaining.