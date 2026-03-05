import sys

from builder.CopyBuilder import CopyBuilder
from src.WiiIsoReader import WiiIsoReader
from src.builder.WiiDiscBuilder import WiiDiscBuilder

def partition_copy(src_path: str, dst_path: str) -> None:
    print(f"Source : {src_path}")
    print(f"Dest   : {dst_path}")

    with WiiIsoReader(src_path) as reader:
        print(f"Game   : {reader.disc_header.game_title.strip()}")
        print(f"ID     : {reader.disc_header.game_id.decode()}")

        builder = WiiDiscBuilder(reader.disc_header, reader.region)

        with open(dst_path, 'w+b') as dest:
            for entry in reader.partitions:
                copy_builder = CopyBuilder(reader, entry, None)
                builder.add_partition(dest, copy_builder, None)

            builder.finish(dest)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        src_path = "../assets/smg.iso"
        dest_path = f"../assets/copied.iso"
    else:
        src_path = sys.argv[1]
        dest_path = sys.argv[2]

    raw_partition_copy(src_path, dest_path)
