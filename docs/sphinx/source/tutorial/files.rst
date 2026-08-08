===============
Files, in depth
===============

Replacing a file is one line. Understanding when that line takes effect and what happens when the file lives
three layers deep inside an archive is what this chapter is

What a path is
==============

A partition stores its files in a file system table, the FST. Despite the name, it is not a tree on disc: it is
a flat array of nodes. A directory node records the index where its contents end, and everything between it and
that index belongs to it. Depth is implied by ranges, not by pointers

That layout has one consequence you will feel: **a directory has no size of its own**, and moving a file between
directories means renumbering everything after it. Wiithon rebuilds the whole array on write, so you never deal
with this, but it explains why there is no "move" operation

Paths use ``/``, are relative to the partition root:

..  code-block:: python

    patcher.read_file("StageData/AstroDome/AstroDome.arc")

Queueing operations
===================

Every modification is recorded and replayed at build time. Reads always hit the source disc

..  code-block:: python

    patcher.replace_file("opening.bnr", new_data)
    patcher.read_file("opening.bnr")      # still the original

This can be tricky. To be simple: the patcher is a **list of intentions** not a mutable
copy of the disc. Nothing you queue is visible to anything else you queue

The practical rule is to hold your own reference to whatever you build, rather than expecting to read it back:

..  code-block:: python

    bnr = BNR.read(BytesIO(patcher.read_file("opening.bnr")))
    bnr.imet.set_title("My hack", language="English")
    patcher.replace_file("opening.bnr", bnr.get_bytes())

Add, replace, remove
====================

The three operations are not symmetric, because two different things are being changed: the FST, and the file
data

================  ============  ============
Operation         Touches FST   Touches data
================  ============  ============
``add_file``      yes           yes
``replace_file``  no            yes
``remove_file``   yes           no
=============== = ============  ============

``replace_file`` leaves the tree alone, so the file must already exist. Its new size is picked up from the data
you pass, which means a replacement may be larger or smaller than the original with no further work

``remove_file`` on a path you queued with ``add_file`` cancels the addition rather than queueing a removal

..  warning::

    Removing a file that the game code references does not fail at build time. It fails when the game tries
    to load it, usually as a crash

Archives
========

Most of a Wii game is not loose files. It is RARC or U8 archives, frequently Yaz0-compressed and the thing you
actually want to change is inside of them

``edit_as`` takes a path that crosses the boundary:

..  code-block:: python

    path = "StageData/AstroDome/AstroDome.arc/stageinfo/layera"

    with patcher.edit_as(path, BCSV, str_fmt="shift_jis") as bcsv:
        ...

There is no separator marking where the disc path stops and the archive path starts. Wiithon finds it by
walking the path from the right and asking the FST which prefix resolves to a **file**. Everything after that
prefix is the path inside the archive

That detail is worth keeping in mind, because it means the extension is irrelevant. An archive named
``foo.dat`` works exactly like one named ``foo.arc``, and a directory that happens to be named ``bar.arc`` will
never be mistaken for one

Compression is peeled automatically. The resolver looks at the first four bytes, and as long as it recognises a
container magic it unwraps and looks again:

..  code-block:: text

    Yaz0  ->  RARC  ->  stageinfo/layera

On write, the layers are rebuilt in reverse order, so a file that arrived Yaz0-compressed leaves
Yaz0-compressed

..  warning::

    Only **one archive level** is supported (currently). A path can cross into an archive, not into an archive inside an
    archive. If you need that, open the outer one as :class:`~wiithon.formats.rarc.Rarc` yourself and work on
    the inner bytes

..  warning::

    Each ``edit_as`` call re-reads from the source disc. Two successive calls on two files of the same archive
    will lose the first edit, because the second call reopens the original archive. Open the archive once and
    make both changes inside a single block

..  seealso::

    :meth:`wiithon.disc.patcher.edit_as` for the API of ``edit_as``. If you want to implement your own class to pass
    through it, it needs ``read(stream, **kwargs)`` and ``write(stream)`` implementation

BCSV
====

BCSV is the format behind most of a game's tunable data: stage lists, object parameters, event tables. It is a
typed table, and its header stores column names as **hashes**

The hash is one-way. A BCSV file genuinely does not know what its own columns are called. Every tool that
displays readable column names, Wiithon included, is matching hashes against a list of names that somebody
guessed and confirmed by hand

..  code-block:: python

    from wiithon import BCSV
    from wiithon.formats.bcsv import calculate_field_hash

    field_names = {
        calculate_field_hash("ScenarioNo"): "ScenarioNo",
        calculate_field_hash("LuigiModeTimer"): "LuigiModeTimer",
    }

    with patcher.edit_as(path, BCSV, field_names=field_names, str_fmt="shift_jis") as bcsv:
        for entry in bcsv.entries:
            entry["LuigiModeTimer"] = 0

Any column you did not name shows up under its stringified hash. That is not an error, and the file writes back
correctly regardless

..  important::

    ``str_fmt`` is not detected. Passing the wrong encoding produces some issues rather than an exception

..  seealso::

    :doc:`/user_guide/file_formats` for the format classes used on their own, and :doc:`rebuilding` for what
    happens to all of this at build time