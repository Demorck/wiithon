========
Glossary
========

Terms you will meet across this documentation

A
-

..  glossary::
    :sorted:

    Apploader
        The small program that loads the game into memory and starts it. It lives at a fixed offset in the
        partition before the file data

    Arena
        The game's heap. Everything between :term:`arenaLo` and ``arenaHi`` is available for runtime
        allocation

    arenaLo
        The lower bound of the :term:`Arena`. It is a constant compiled into the boot code, not a value read
        from anywhere, which is why moving it means patching an instruction. See
        :doc:`/tutorial/code_injection`

B
-

..  glossary::
    :sorted:

    boot.bin
        A second disc header. Stored at offset 0 of the *decrypted* partition data. It carries what the outer
        header cannot know: the offsets of the :term:`DOL` and the :term:`FST`. Extraction tools call it
        ``boot.bin``. It's like the header of each partition

    bi2.bin
        A configuration block sitting right after the internal header, holding some parameters. If you have
        any sourced information of it, i'm taking them

    Block
        The unit of partition encryption: ``0x8000`` bytes of which ``0x400`` are a hash header and ``0x7C00``
        are encrypted data

    BCSV
        A typed table format holding most of a game's tunable data. Column names are stored as hashes so readable names
        have to be supplied from outside. See :doc:`/tutorial/files`

    BNR
    opening.bnr
        The banner file shown in the Wii menu. An :term:`IMET` header followed by a :term:`U8` archive
        containing the icon, the banner and the sound

    bss
        Means `Block Started by Symbol`. It's not a specific of Nintendo consoles. The memory section of BSS is used for
        constants and static object. This section is zeroed at load time. Its end is **not** the start of the
        :term:`Arena`: measured across games, ``arenaLo`` sits about ``0x10000`` higher

C
-

..  glossary::
    :sorted:

    Common key
        One of Nintendo's global AES keys used to decrypt every :term:`Title key`. Index 0 is the normal key,
        index 1 the Korean one and index 2 the Wii U in Wii mode

    CMD
    Content metadata
        One entry of a :term:`TMD`, describing a single content: its ID, index, type, size and SHA-1

    Certificate chain
        The three certificates that would validate a :term:`Ticket` and a :term:`TMD` signature on real
        hardware

    Code cave
        A run of unused bytes inside an existing section, usually ``nop`` or zeros large enough to hold a
        small routine. The cheapest place to put code since it needs no new section

D
-

..  glossary::
    :sorted:

    Disc header
        The first ``0x440`` bytes of an ISO unencrypted. Holds the :term:`Game ID`, the title and the flags
        that disable encryption or hash verification. See :doc:`/internal/iso`

    DOL
        The executable format of Wii games. Up to 7 text and 11 data sections, each declaring the
        virtual address it must load at. See :doc:`/tutorial/dol`

    Dolphin
        The GameCube and Wii emulator (and also the internal project codename for Gamecube)

F
-

..  glossary::
    :sorted:

    FST
    File System Table
        The list of files and directories in a partition. It's stored as a flat array of
        nodes, not a tree: a directory records the index where its contents end. See :doc:`/tutorial/files`

    Fakesign
        Zeroing a signature and brute-forcing a padding field until the SHA-1 of the signed blob starts with a
        null byte. This exploits a check in the original IOS that compared only the first byte. Also known as Trucha bug

G
-

..  glossary::
    :sorted:

    Game ID
        Six ASCII characters identifying a release such as ``RMGE01``. The first letter is the console, the
        next two the game, fourth the region, the last two the publisher. (Might be wrong, i don't find any source
        of it)

    Group
        64 :term:`Block` s subdivided into 8 subgroups of 8 blocks. Hashing and encryption operate a group at
        a time which is why changing one byte costs a whole group

H
-

..  glossary::
    :sorted:

    H0
    H1
    H2
    H3
        The four levels of the partition hash tree. ``H0`` hashes the 31 subblocks of a block, ``H1`` the 8
        blocks of a subgroup, ``H2`` the 8 subgroups of a group and ``H3`` each group. The ``H3`` table lives
        outside the encrypted data and is itself hashed into the :term:`TMD`

    Hook
        Replacing an existing instruction with a branch to your own code, which runs and then returns

I
-

..  glossary::
    :sorted:

    IV
    Initialization vector
        The starting state of an AES-CBC operation. Each encrypted :term:`Block` stores its own at offset
        ``0x3D0`` of its header

    IMET
        The header of a :term:`BNR`, holding the game title in ten languages

    IMD5
        A small header with an MD5 checksum, wrapping the assets inside a banner

L
-

..  glossary::
    :sorted:

    LZ77
        A compression format used inside banner assets, distinct from :term:`Yaz0`

M
-

..  glossary::
    :sorted:

    Magic word
        A sequence of bytes that identifies the file type. ``0x5D1C9EA3`` at offset ``0x18`` marks a Wii
        :term:`Disc header` for example.

    Merkle tree
        A tree in which every non-leaf node is a hash of its children. The Wii partition hash tree is one of it and
        it is what makes in-place editing impossible. See :doc:`/tutorial/rebuilding`

    MEM1
        The 24 MB of main memory mapped from ``0x80000000``. Game code and most data live here

    MEM2
        An additional 64 MB mapped from ``0x90000000``

P
-

..  glossary::
    :sorted:

    Partition
        A self-contained individually encrypted section of the disc. ``DATA`` holds the game, ``UPDATE`` holds
        a system update, ``CHANNEL`` holds virtual channel titles. Wiithon reads and patches ``DATA`` for now

    Partition table
        A table at ``0x40000`` describing up to four groups of partitions, each entry giving an offset and a
        type

    PowerPC
    Broadway
        The Wii's CPU. 32-bit big endian and fixed four-byte instructions. See :doc:`/tutorial/ppc`

R
-

..  glossary::
    :sorted:

    RARC
        Nintendo's archive format, used to bundle game assets. Frequently wrapped in :term:`Yaz0`

T
-

..  glossary::
    :sorted:

    Ticket
        The structure holding the encrypted :term:`Title key`. One per partition and stored at its very start

    Title key
        The AES-128 key that encrypts a partition's data. It is stored encrypted in the :term:`Ticket` and
        decrypted with a :term:`Common key`

    TMD
    Title metadata
        Describes a title and its contents with a SHA-1 hash per content. It also carries the hash of the
        :term:`H3` table, which is why it can only be finalised once the partition is fully encrypted

    TPL
        Nintendo's texture format found inside banner archives

U
-

..  glossary::
    :sorted:

    U8
        A simpler archive format used for banners and channel content

V
-

..  glossary::
    :sorted:

    Virtual address
        The address a section is loaded at as opposed to its offset in the DOL file. All patching APIs in
        Wiithon take virtual addresses

W
-

..  glossary::
    :sorted:

    wit
        The Wiimms ISO Tools, a command line suite for extracting and rebuilding Wii discs. The directory
        layout ``DirectoryPartitionSource`` expects is the one ``wit`` produces

    WiiBrew
        The community wiki documenting the Wii's formats and internals. Most of what :doc:`/internal/iso` 
        describes was reverse engineered there first

Y
-

..  glossary::
    :sorted:

    Yaz0
        A run-length compression format