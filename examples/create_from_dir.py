from builder.DirectoryPartitionBuilder import DirectoryPartitionBuilder
from builder.WiiDiscBuilder import WiiDiscBuilder
from helpers.Enums import WiiPartType

def main():
    dir_builder = DirectoryPartitionBuilder("src", WiiPartType.DATA)
    with open("../assets/copied_dir.iso", "w+b") as dest:
        builder = WiiDiscBuilder(dir_builder.encrypted_header, dir_builder.region)
        builder.add_partition(dest, dir_builder, None)

        builder.finish(dest)


if __name__ == "__main__":
    main()