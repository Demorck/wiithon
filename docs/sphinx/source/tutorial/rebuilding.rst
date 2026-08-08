===================
Rebuilding the disc
===================

``build()`` is where every queued change becomes an ISO. It is also the slowest thing Wiithon does

Nothing is patched in place
===========================

There is no such thing as editing a Wii ISO in place. Every partition is written again from the beginning, and
the source disc is only ever read

That is not a design preference, it is forced by the format. Partition data is stored in blocks of ``0x8000``
bytes and each block carries hashes of its own contents. Those hashes feed into a tree covering the whole
partition whose root ends up in the TMD (Title metadata). Change one byte of one file and the hashes of its block, its
subgroup, and its group all change

..  code-block:: text

    file byte
      -> block hash (H0)
        -> subgroup hash (H1)
          -> group hash (H2)
            -> H3 table
              -> TMD

So an incremental rebuild would have to recompute most of the tree anyway. Rewriting everything is simpler and
barely slower

..  seealso::

    :doc:`/internal/iso` has the block layout and the sequence diagrams for the hash tree

What happens, in order
======================

For each partition:

#. the certificate chain is written unencrypted, after the space reserved for the ticket and the TMD
#. an encrypting writer is opened over the data area
#. ``bi2``, the apploader, the DOL and the FST are written, and the DOL and FST offsets are recorded in the
   internal disc header as each one lands
#. every file is written in FST order, each aligned to a boundary, and **each node's offset and length are
   rewritten as the file lands**
#. the total size is rounded up to a whole number of encryption groups
#. the FST is written a second time, now that every offset is known
#. the internal disc header is written at offset 0 of the data area
#. the writer is closed, which finalises the hash tree, and the H3 table is written
#. the TMD is fakesigned against that H3 table, then written
#. the partition header, which carries the ticket, is written at the very start of the partition
 

Then, once for the disc, the header, the partition table, the region and the magic word are written

Step 4 is the one worth remembering. **The offsets in the FST you hand to the builder are ignored.** They are
overwritten with wherever the file actually ended up. This is why replacing a file with a bigger one needs no
special handling, and why you never compute an offset yourself

Size
====

The output is usually not the same size as the input, for three reasons that stack:

* files are aligned, so a file one byte long still consumes a full alignment unit
* each partition is padded up to a whole encryption group, ``0x8000 * 64`` bytes of raw capacity
* your own additions

A rebuilt disc is often slightly **smaller** than the original, because retail discs pad up to the physical
medium size and Wiithon does not

..  note::

    Plan for free space of roughly the size of the source ISO. The output is written directly, not buffered in
    memory, but the source stays open the whole time

..  note::
    
    It's planned that wiithon optimize partitions and data so the ISO could be as small as possible

Progress
========

``build()`` takes a callback, called with a percentage from 0 to 100:

..  code-block:: python

    patcher.build("patched.iso", progress_cb=lambda pct: print(f"\\r{pct}%", end=""))

It restarts at 0 for every partition, since the builder has no idea how many will follow

Signatures
==========

The TMD is fakesigned: the real signature is zeroed, and the padding is brute-forced until the SHA-1 of the
signed blob starts with a null byte. This exploits the signature check of the original IOS

Verifying
=========

The cheapest check is to reopen what you just wrote:

..  code-block:: python

    from wiithon import WiiIsoReader

    with WiiIsoReader("patched.iso") as reader:
        partition = reader.open_partition(reader.get_data_partition())

        print(reader.disc_header.game_title)
        print(len(partition.list_files()), "files")
        print(len(partition.read_file("opening.bnr")), "bytes")

If the partition opens, the title key decrypted correctly, the hashes are consistent and the FST parsed
That rules out most of what can go wrong structurally

..  tip::

    Keep a build that works. When a patch breaks the game, the useful question is what changed since the last
    good build, and that question is much easier to answer when the last good build still exists