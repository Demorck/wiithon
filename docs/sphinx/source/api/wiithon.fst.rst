===========
wiithon.fst
===========

The file system table of a partition: the tree of directories and files, and its
serialisation back to disc.

..  toctree::
    :maxdepth: 1

    wiithon.fst.tree
    wiithon.fst.node
    wiithon.fst.operations
    wiithon.fst.serializer
    wiithon.fst.raw_node

..  rubric:: Modules

:doc:`wiithon.fst.tree`
    The ``FST`` itself: reading, writing and lookup.

:doc:`wiithon.fst.node`
    Nodes of the tree: the abstract node, files and directories.

:doc:`wiithon.fst.operations`
    Finding, adding and removing a node by path.

:doc:`wiithon.fst.serializer`
    Turns a tree back into the flat node array and string table stored on disc.

:doc:`wiithon.fst.raw_node`
    The 12-byte on-disc representation of a node.