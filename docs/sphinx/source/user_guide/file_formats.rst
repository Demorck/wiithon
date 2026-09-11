============
File Formats
============

Wiithon can parse several Nintendo formats directly, whether they come from an ISO
or from a standalone file on disk.

..  note::

    Every format class follows the same shape: ``read(stream)`` to parse,
    ``write(stream)`` or ``get_bytes()`` to serialise back. All of them are
    importable from the top-level package, for example ``from wiithon import Rarc``.

..  tip::

    To edit a file that lives *inside* an ISO. possibly nested in an archive.
    you usually want ``patcher.edit_as()`` rather than these classes directly.
    See :doc:`patching`.

RARC
----

RARC is Nintendo's archive format, used to bundle multiple files into one.

..  code-block:: python

    from io import BytesIO
    from wiithon import Rarc

    with open("archive.arc", "rb") as f:
        rarc = Rarc.read(f)

    # Listing
    for entry in rarc.entries:
        print(entry.name, entry.data_size)

    # Reading and replacing, by name
    data = rarc.get_file("model.bmd")
    rarc.replace_file("model.bmd", new_data)

    # ...or by full path inside the archive
    data = rarc.get_file_by_path("scene/model.bmd")
    rarc.replace_file_by_path("scene/model.bmd", new_data)

    # Serialising back
    result = rarc.get_bytes()

    # Extracting to disk
    rarc.extract_to("output/")

..  seealso::

    :doc:`/internal/rarc` for the on-disc structure and the hashing scheme.

Yaz0
----

Yaz0 is Nintendo's compression format. Many RARC archives are Yaz0-compressed.
look for the ``Yaz0`` magic bytes at offset 0.

..  code-block:: python

    from io import BytesIO
    from wiithon import Yaz0

    # Decompressing
    with open("file.szs", "rb") as f:
        yaz0 = Yaz0.read(f)
    raw = yaz0.data

    # Compressing
    compressed = Yaz0.from_data(raw)
    result = compressed.get_bytes()

..  important::

    ``Yaz0.read()`` decompresses immediately: ``yaz0.data`` is the *uncompressed*
    payload, not the compressed stream. Reading a non-Yaz0 file raises
    ``InvalidFormatError``.

..  seealso::

    :doc:`/internal/yaz0` for the block and pointer encoding.

U8
--

U8 is the archive format used for banners and channel content.

..  code-block:: python

    from wiithon import U8

    with open("banner.bin", "rb") as f:
        u8 = U8.read(f)

    data = u8.get_file("meta/banner.tpl")
    u8.replace_file("meta/banner.tpl", new_data)

    u8.extract_to("output/")
    result = u8.get_bytes()

BNR
---

``opening.bnr`` holds the banner shown in the Wii menu: the localised titles
(IMET header) plus an embedded U8 archive with the icon, banner and sound.

..  code-block:: python

    from io import BytesIO
    from wiithon import BNR

    bnr = BNR.read(BytesIO(patcher.read_file("opening.bnr")))

    print(bnr.title)

    bnr.imet.set_title("Modded game", language="English")

    icon   = bnr.get_icon()      # meta/icon.bin
    banner = bnr.get_banner()    # meta/banner.bin
    sound  = bnr.get_sound()     # meta/sound.bin

    bnr.replace_sound(custom_sound)

    patcher.replace_file("opening.bnr", bnr.get_bytes())

..  note::

    For a simple title change, ``patcher.modify_banner_title()`` does all of the
    above in one call.

DOL
---

The DOL is the main executable format for GameCube and Wii games.

..  code-block:: python

    from wiithon import DOL

    with open("main.dol", "rb") as f:
        dol = DOL.read(f)

    value = dol.read_at(0x80123456, 4)
    dol.write_at(0x80123456, b"\\xde\\xad\\xbe\\xef")

    result = dol.to_bytes()

..  seealso::

    :doc:`patching` for injecting new code, and :doc:`/internal/powerpc` for the
    PowerPC instruction encodings.

BCSV
----

BCSV is a table format. Think of a CSV with a typed, hashed header. Field names
are stored as hashes, so you have to supply the names you expect.

..  code-block:: python

    from wiithon import BCSV
    from wiithon.formats.bcsv import calculate_field_hash

    field_names = {
        calculate_field_hash("ScenarioNo"): "ScenarioNo",
    }

    bcsv = BCSV.read(stream, field_names=field_names, str_fmt="shift_jis")

    for entry in bcsv.entries:
        print(entry["ScenarioNo"])

..  warning::

    The hash-to-name function is one-way: a field whose name you did not supply
    shows up under its stringified hash. Passing the wrong ``str_fmt`` silently
    produces some issues rather than an error. ``shift_jis`` is the usual choice
    for Japanese-developed titles.

LZ77
----

LZ77 compression, used inside banner assets.

..  code-block:: python

    from wiithon import Lz77

    compressed = Lz77.compress(raw_data)
    raw_data   = Lz77.uncompress(compressed, len(raw_data))