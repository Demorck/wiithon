===============
wiithon.formats
===============

Nintendo file formats, readable and writable independently of any ISO.

Every class follows the same shape: ``read(stream)`` to parse, ``write(stream)``
or ``get_bytes()`` to serialise back.

..  toctree::
    :maxdepth: 1

    wiithon.formats.rarc
    wiithon.formats.u8
    wiithon.formats.yaz0
    wiithon.formats.lz77
    wiithon.formats.dol
    wiithon.formats.dol_header
    wiithon.formats.bcsv
    wiithon.formats.bnr
    wiithon.formats.imet
    wiithon.formats.imd5
    wiithon.formats.archive

..  rubric:: Archives

:doc:`wiithon.formats.rarc`
    Nintendo archive format, used to bundle game assets.

:doc:`wiithon.formats.u8`
    Archive format used by banners and channel content.

..  rubric:: Compression

:doc:`wiithon.formats.yaz0`
    Run-length compression, common on RARC archives.

:doc:`wiithon.formats.lz77`
    LZ77 compression, used inside banner assets.

..  rubric:: Executable

:doc:`wiithon.formats.dol`
    The main game executable, with section access and code injection.

:doc:`wiithon.formats.dol_header`
    Section table of a DOL.

..  rubric:: Data

:doc:`wiithon.formats.bcsv`
    Typed table format with hashed column names.

:doc:`wiithon.formats.bnr`
    ``opening.bnr``, the banner shown in the Wii menu.

:doc:`wiithon.formats.imet`
    IMET header of a banner, holding the localised titles.

:doc:`wiithon.formats.imd5`
    IMD5 header and checksum, wrapping banner assets.

..  rubric:: Protocols

:doc:`wiithon.formats.archive`
    Structural types describing what an archive and a container must provide,
    used by ``WiiIsoPatcher.edit_as``.

..  seealso::

    :doc:`/user_guide/file_formats` for task-oriented examples, and
    :doc:`/internal/rarc` and :doc:`/internal/yaz0` for the on-disc encodings.