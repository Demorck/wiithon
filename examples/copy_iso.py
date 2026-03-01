import sys

from WiiIsoReader import WiiIsoReader
from builder.CopyBuilder import CopyBuilder
from builder.WiiDiscBuilder import WiiDiscBuilder

def copy_iso(src_path: str, dst_path: str) -> None:
    print(f"Source : {src_path}")
    print(f"Dest   : {dst_path}")

    with WiiIsoReader(src_path) as reader:
        print(f"Game   : {reader.disc_header.game_title.strip()}")
        print(f"ID     : {reader.disc_header.game_id.decode()}")

        builder = WiiDiscBuilder(reader.disc_header, reader.region)

        with open(dst_path, 'wb') as dest:
            for entry in reader.partitions:
                type_name = {0: "DATA", 1: "UPDATE", 2: "CHANNEL"}.get(entry.part_type, f"?{entry.part_type}")
                print(f"\n[Partition {type_name} @ 0x{entry.offset:X}]")

                partition = reader.open_partition(entry)
                copy_builder = CopyBuilder(entry, partition)

                def progress(pct, label=type_name):
                    bar = 'X' * (pct // 5) + 'O' * (20 - pct // 5)
                    print(f"\r  {label} [{bar}] {pct:3d}%", end='', flush=True)

                file_count = builder.add_partition(dest, copy_builder, progress_cb=progress)
                print(f"\n  {file_count} files copied")

            builder.finish(dest)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        src_path = "../assets/smg.iso"
        dest_path = "../assets/smg_rebuilt.iso"
    else:
        src_path = sys.argv[1]
        dest_path = sys.argv[2]

    copy_iso(src_path, dest_path)
