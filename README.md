# Wiithon

A Python library for reading, extracting, and rebuilding Nintendo Wii ISO files. 

## Features

* Parse and extract files from standard Wii ISOs.
* Read the Wii File System Table (FST) and reconstruct the directory tree.
* On-the-fly decryption and encryption of Wii data clusters.
* Rebuild and master new Wii ISOs from extracted or modified files.
* Hash calculation and Merkle tree generation for partition integrity. (doesn't work great atm)

## Documentation

For comprehensive guides, internal architecture details, and references, please refer to the [docs/](docs/) directory.

## Examples

For some examples, you can refer to the [examples/](examples/) directory.

## Overview

The library is divided into two main components: reading existing ISOs and building new ones.

### Reading and Extracting

To read an ISO, initialize the `WiiIsoReader` with a binary stream. You can iterate through the partitions and access the decrypted file data using the FST offsets.
(currently just copied/paste the examples in the above directory)
```python
from WiiIsoReader import WiiIsoReader

# Opening the ISO
with WiiIsoReader("your_iso_file.iso") as reader:
    print(f"Game: {reader.disc_header.game_title}")

    data = reader.get_data_partition()
    partition = reader.open_partition(data)

    for path in partition.list_files():
        print(path)

    print(f"Number of files: {len(partition.list_files())}")
```

### Building
To build an ISO, you can use some interfaces. Each interface has their specificities like copying an ISO, patching an ISO or building from a folder from your explorer.
Currently, only the copy one exists.

```python
from builder.CopyBuilder import CopyBuilder
from WiiIsoReader import WiiIsoReader
from builder.WiiDiscBuilder import WiiDiscBuilder

SOURCE_PATH = "your_iso_file.iso"
DEST_PATH   = "output_iso.iso"

print(f"Source : {SOURCE_PATH}")
print(f"Dest   : {DEST_PATH}")

# Open the original ISO
with WiiIsoReader(SOURCE_PATH) as reader:
    print(f"Game   : {reader.disc_header.game_title.strip()}")
    print(f"ID     : {reader.disc_header.game_id.decode()}")

    # The main builder
    builder = WiiDiscBuilder(reader.disc_header, reader.region)

    with open(DEST_PATH, 'w+b') as dest:
        # For each partition from the original ISO
        for entry in reader.partitions:
            # Copying and build into the new one
            copy_builder = CopyBuilder(reader, entry, None)
            builder.add_partition(dest, copy_builder, None)

        # To write the header and partitions datas 
        builder.finish(dest)
```

## TODO
### Done
- [x] Fixing the H3 table (Dolphin says that is not correct :( ) 
- [x] Fixing a thing that dolphin says: some block are incorrect but unused
- [x] Adding more WiiPartitionInterface from dir
---
### Next to do
- [ ] Refactor/adding constants to avoid magic numbers
- [ ] Comment all functions (and inside of it)
- [ ] Some docs about building and so on
---
### Next after next (ordered)

- [ ] Patcher !!
- [ ] Adding some tools like Yaz0 extractor and so on
- [ ] Add more unit tests (and change some)
- [ ] Improve exception handling for invalid or corrupted ISO headers
- [ ] Add a CLI for standard extraction and building