====================
wiithon.disc.structs
====================

Binary structures stored on the disc, each with a ``read`` and a ``write``
method mapping one to one onto its on-disc layout.

You rarely build these by hand. They are produced by
:class:`~wiithon.disc.reader.WiiIsoReader` and exposed as attributes of
:class:`~wiithon.disc.partition.WiiPartitionInfo`.

..  toctree::
    :maxdepth: 1

    wiithon.disc.structs.disc_header
    wiithon.disc.structs.partition_entry
    wiithon.disc.structs.partition_header
    wiithon.disc.structs.ticket
    wiithon.disc.structs.ticket_time_limit
    wiithon.disc.structs.tmd
    wiithon.disc.structs.tmd_content
    wiithon.disc.structs.certificate
    wiithon.disc.structs.signature
    wiithon.disc.structs.apploader_header

..  rubric:: Modules

:doc:`wiithon.disc.structs.disc_header`
    Disc header, both the unencrypted one at offset ``0x000`` and the internal
    one found in the decrypted data.

:doc:`wiithon.disc.structs.partition_entry`
    Entries of the partition table, giving the offset and type of each partition.

:doc:`wiithon.disc.structs.partition_header`
    Header of a partition, holding the ticket and the offsets to the TMD,
    certificates, H3 table and data.

:doc:`wiithon.disc.structs.ticket`
    Ticket, holding the encrypted title key.

:doc:`wiithon.disc.structs.ticket_time_limit`
    Time limit entries of a ticket.

:doc:`wiithon.disc.structs.tmd`
    Title metadata, describing the contents of a title.

:doc:`wiithon.disc.structs.tmd_content`
    A single content entry of a TMD, with its SHA-1 hash.

:doc:`wiithon.disc.structs.certificate`
    Certificate of the signing chain.

:doc:`wiithon.disc.structs.signature`
    Signature and key type enumerations, which determine the size of a
    certificate.

:doc:`wiithon.disc.structs.apploader_header`
    Header of the apploader, declaring its two payload sizes.

..  seealso::

    :doc:`/internal/iso` documents every field and offset of these structures.